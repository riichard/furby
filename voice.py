#!/usr/bin/env python3
"""AudioIO: microphone recording (VAD), Whisper STT, OpenAI TTS, and playback."""

import io
import os
import struct
import subprocess
import tempfile
import wave

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pyaudio
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000    # Hz — Whisper works best at 16 kHz
CHANNELS = 1
BYTES_PER_SAMPLE = 2

# ALSA device for recording (arecord -D <device>)
# Uses plughw for automatic format conversion
RECORD_DEVICE = os.getenv("FURBY_MIC_DEVICE", "plughw:1,0")

# Voice Activity Detection
CHUNK_MS = 50
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)
RMS_THRESHOLD = 45         # fallback if calibration fails
SILENCE_TIMEOUT_S = 1.5
MIN_SPEECH_FRAMES = 10     # minimum chunks to consider a valid recording
NOISE_CALIBRATION_S = 1.5  # seconds to sample ambient noise at startup
SPEECH_RATIO = 3.0         # threshold = noise_floor * this multiplier


class AudioIO:
    def __init__(self):
        self.client = OpenAI()
        self.rms_threshold = self._calibrate_noise()

    def _calibrate_noise(self):
        """Sample ambient noise for NOISE_CALIBRATION_S seconds, set threshold."""
        print("[voice] Calibrating noise floor (be quiet)...")
        cmd = [
            "arecord", "-D", RECORD_DEVICE,
            "-f", "S16_LE", "-r", str(SAMPLE_RATE), "-c", str(CHANNELS),
            "-q", "-",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        bytes_per_chunk = CHUNK_FRAMES * BYTES_PER_SAMPLE * CHANNELS
        n_chunks = int(NOISE_CALIBRATION_S * 1000 / CHUNK_MS)
        rms_values = []
        try:
            for _ in range(n_chunks):
                data = proc.stdout.read(bytes_per_chunk)
                if data:
                    rms_values.append(_rms(data))
        finally:
            proc.terminate()
            proc.wait()

        if not rms_values:
            print(f"[voice] Noise calibration failed, using default threshold {RMS_THRESHOLD}")
            return RMS_THRESHOLD

        noise_floor = sum(rms_values) / len(rms_values)
        threshold = max(RMS_THRESHOLD, noise_floor * SPEECH_RATIO)
        print(f"[voice] Noise floor: {noise_floor:.1f}, speech threshold: {threshold:.1f}")
        return threshold

    # ------------------------------------------------------------------
    # Recording via arecord (reliable on Pi with USB mic)
    # ------------------------------------------------------------------

    def _beep(self, freq=880, duration_ms=120):
        """Play a short beep through the speaker to signal ready-to-listen."""
        import math
        rate = 22050
        n = int(rate * duration_ms / 1000)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            samples = bytes(
                struct.pack("<h", int(32767 * math.sin(2 * math.pi * freq * i / rate)))
                for i in range(n)
            )
            wf.writeframes(samples)
        self.play(buf.getvalue())

    def record_until_silence(self):
        """
        Stream from mic via arecord, apply VAD, return WAV bytes when silence.
        """
        self._beep()
        print("[voice] Listening for speech...")

        cmd = [
            "arecord",
            "-D", RECORD_DEVICE,
            "-f", "S16_LE",
            "-r", str(SAMPLE_RATE),
            "-c", str(CHANNELS),
            "-q",   # suppress arecord status messages
            "-",    # output to stdout
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        frames = []
        speech_started = False
        silent_chunks = 0
        silent_chunks_needed = int(SILENCE_TIMEOUT_S * 1000 / CHUNK_MS)
        bytes_per_chunk = CHUNK_FRAMES * BYTES_PER_SAMPLE * CHANNELS

        try:
            while True:
                data = proc.stdout.read(bytes_per_chunk)
                if not data:
                    break

                rms = _rms(data)

                if not speech_started:
                    if rms > self.rms_threshold:
                        print("[voice] Speech detected, recording...")
                        speech_started = True
                        frames.append(data)
                else:
                    frames.append(data)
                    if rms < self.rms_threshold:
                        silent_chunks += 1
                        if silent_chunks >= silent_chunks_needed:
                            print("[voice] Silence detected, stopping.")
                            break
                    else:
                        silent_chunks = 0
        finally:
            proc.terminate()
            _, stderr = proc.communicate()
            if stderr:
                print(f"[voice] arecord: {stderr.decode().strip()}")

        if len(frames) < MIN_SPEECH_FRAMES:
            print("[voice] Recording too short, ignoring.")
            return None

        return _frames_to_wav(frames)

    # ------------------------------------------------------------------
    # STT via Whisper
    # ------------------------------------------------------------------

    def transcribe(self, wav_bytes):
        """Send WAV bytes to Whisper API, return transcription string."""
        wav_file = io.BytesIO(wav_bytes)
        wav_file.name = "audio.wav"
        result = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=wav_file,
        )
        text = result.text.strip()
        print(f"[voice] Transcribed: {text!r}")
        return text

    # ------------------------------------------------------------------
    # TTS via OpenAI
    # ------------------------------------------------------------------

    def synthesize(self, text, voice="nova"):
        """Convert text to WAV bytes using OpenAI TTS."""
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="wav",
        )
        wav_bytes = response.content
        print(f"[voice] Synthesized {len(wav_bytes)} bytes of audio.")
        return wav_bytes

    # ------------------------------------------------------------------
    # Playback via PyAudio
    # ------------------------------------------------------------------

    def play(self, wav_bytes):
        """Play WAV bytes through default audio output."""
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
            )
            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.stop_stream()
            stream.close()
            pa.terminate()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rms(data):
    """Compute RMS amplitude of a 16-bit PCM chunk."""
    count = len(data) // BYTES_PER_SAMPLE
    if count == 0:
        return 0
    shorts = struct.unpack(f"{count}h", data)
    return (sum(s * s for s in shorts) / count) ** 0.5


def _frames_to_wav(frames):
    """Pack raw PCM frames into an in-memory WAV byte string."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(BYTES_PER_SAMPLE)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    audio = AudioIO()
    while True:
        print("Recording — speak a sentence...")
        wav = audio.record_until_silence()
        if wav:
            print(f"Recorded {len(wav)} WAV bytes.")
            break
        print("Nothing captured, trying again...")

    text = audio.transcribe(wav)
    print(f"Transcription: {text}")

    print("Synthesizing TTS...")
    tts = audio.synthesize(f"You said: {text}")
    print("Playing back...")
    audio.play(tts)
    print("Done.")
