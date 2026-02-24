#!/usr/bin/env python3
"""AudioIO: microphone recording (VAD), Whisper STT, OpenAI TTS, and playback."""

import io
import os
import struct
import time
import wave

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import numpy as np
import pyaudio
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHUNK_MS = 50          # recording chunk size in milliseconds
SAMPLE_RATE = 16000    # Hz — Whisper works best at 16 kHz
CHANNELS = 1
FORMAT = pyaudio.paInt16
BYTES_PER_SAMPLE = 2

CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)

# Voice Activity Detection thresholds
RMS_THRESHOLD = 500    # RMS amplitude to consider "speech"
SILENCE_TIMEOUT_S = 1.5   # seconds of silence before stopping recording
MIN_SPEECH_S = 0.3        # minimum duration to keep a recording


class AudioIO:
    def __init__(self):
        self.client = OpenAI()  # reads OPENAI_API_KEY from environment

    # ------------------------------------------------------------------
    # Recording with VAD
    # ------------------------------------------------------------------

    def record_until_silence(self):
        """
        Block until speech is detected, then record until 1.5s of silence.
        Returns raw WAV bytes (16-bit, 16 kHz, mono).
        """
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_FRAMES,
        )

        print("[voice] Listening for speech...")
        frames = []
        speech_started = False
        silent_chunks = 0
        silent_chunks_needed = int(SILENCE_TIMEOUT_S * 1000 / CHUNK_MS)

        try:
            while True:
                data = stream.read(CHUNK_FRAMES, exception_on_overflow=False)
                rms = _rms(data)

                if not speech_started:
                    if rms > RMS_THRESHOLD:
                        print("[voice] Speech detected, recording...")
                        speech_started = True
                        frames.append(data)
                else:
                    frames.append(data)
                    if rms < RMS_THRESHOLD:
                        silent_chunks += 1
                        if silent_chunks >= silent_chunks_needed:
                            print("[voice] Silence detected, stopping.")
                            break
                    else:
                        silent_chunks = 0
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        return _frames_to_wav(frames)

    # ------------------------------------------------------------------
    # STT via Whisper
    # ------------------------------------------------------------------

    def transcribe(self, wav_bytes):
        """Send WAV bytes to Whisper API, return transcription string."""
        wav_file = io.BytesIO(wav_bytes)
        wav_file.name = "audio.wav"  # required by openai client
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
    # Standalone playback (used when expressions.py handles playback separately)
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
    shorts = struct.unpack(f"{count}h", data)
    if count == 0:
        return 0
    sq_sum = sum(s * s for s in shorts)
    return (sq_sum / count) ** 0.5


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
    print("Recording — speak a sentence...")
    wav = audio.record_until_silence()
    print(f"Recorded {len(wav)} WAV bytes.")

    text = audio.transcribe(wav)
    print(f"Transcription: {text}")

    print("Synthesizing TTS...")
    tts = audio.synthesize(f"You said: {text}")
    print("Playing back...")
    audio.play(tts)
    print("Done.")
