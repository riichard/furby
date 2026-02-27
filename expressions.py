#!/usr/bin/env python3
"""FurbyExpressionManager: expression control, idle animation, and lip sync."""

import re
import time
import threading
import random
import io
import wave
import yaml


def count_syllables(word):
    """Estimate syllable count via vowel-group heuristic."""
    return max(1, len(re.findall(r'[aeiouAEIOU]+', word)))


def estimate_syllables(text):
    """Count total syllables in a string."""
    return sum(count_syllables(w) for w in re.findall(r"[a-zA-Z']+", text))


class FurbyExpressionManager:
    def __init__(self, furby, config_path="config/expressions.yaml"):
        self.furby = furby
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.expressions = self.config["expressions"]
        self.emotion_map = self.config.get("emotion_map", {})
        self.idle_cfg = self.config["idle"]
        self.lip_cfg = self.config["lip_sync"]

        self._idle_thread = None
        self._idle_stop = threading.Event()
        self._animation_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Expression primitives
    # ------------------------------------------------------------------

    def set_expression(self, name):
        """Move dial to a named expression position."""
        if name not in self.expressions:
            print(f"[expressions] Unknown expression: {name!r}, using neutral")
            name = "neutral"
        pos = self.expressions[name]["position"]
        self.furby.moveTo(pos)

    def _emotion_to_expression(self, emotion):
        """Resolve Claude emotion string to an expression name."""
        return self.emotion_map.get(emotion, "neutral")

    # ------------------------------------------------------------------
    # Idle loop
    # ------------------------------------------------------------------

    def start_idle(self):
        """Start background idle drift animation."""
        self._idle_stop.clear()
        self._idle_thread = threading.Thread(target=self._idle_loop, daemon=True)
        self._idle_thread.start()

    def stop_idle(self):
        """Stop background idle drift animation and wait for it to finish."""
        self._idle_stop.set()
        if self._idle_thread and self._idle_thread.is_alive():
            self._idle_thread.join(timeout=5)

    def _idle_loop(self):
        base_name = self.idle_cfg["base_expression"]
        base_pos = self.expressions[base_name]["position"]
        drift = self.idle_cfg["drift_range"]
        interval = self.idle_cfg["drift_interval_s"]

        while not self._idle_stop.is_set():
            with self._animation_lock:
                offset = random.uniform(-drift, drift)
                target = max(0, min(100, base_pos + offset))
                self.furby.moveTo(target)
            self._idle_stop.wait(timeout=interval)

    # ------------------------------------------------------------------
    # Dance
    # ------------------------------------------------------------------

    def dance(self, duration_s=5.0):
        """Wiggle Furby rapidly — silly dance moves. Blocking; restores idle after."""
        self.stop_idle()
        end = time.time() + duration_s
        # Alternating sweeps at random tempo — chaotic and fun
        positions = [15, 85, 25, 75, 30, 70, 40, 60, 50, 20, 80]
        while time.time() < end:
            for pos in positions:
                if time.time() >= end:
                    break
                with self._animation_lock:
                    self.furby.moveTo(pos)
                time.sleep(random.uniform(0.12, 0.30))
        self.start_idle()

    # ------------------------------------------------------------------
    # Lip sync
    # ------------------------------------------------------------------

    def lip_sync(self, text, audio_duration_ms):
        """Alternate open/closed mouth at syllable rate for audio_duration_ms."""
        open_expr = self.lip_cfg["open"]
        closed_expr = self.lip_cfg["closed"]
        ms_per_syllable = self.lip_cfg["ms_per_syllable"]

        syllables = estimate_syllables(text)
        if syllables == 0:
            syllables = 1

        # Total beat duration matches audio; each syllable = one open+close pair
        beat_ms = audio_duration_ms / syllables
        half_beat_s = (beat_ms / 2) / 1000.0

        start = time.time()
        end = start + audio_duration_ms / 1000.0
        toggle = True
        while time.time() < end:
            with self._animation_lock:
                self.set_expression(open_expr if toggle else closed_expr)
            toggle = not toggle
            time.sleep(max(0.05, half_beat_s))

    # ------------------------------------------------------------------
    # Animated speech
    # ------------------------------------------------------------------

    def animate_speech(self, text, audio_bytes, emotion):
        """
        Full speech animation sequence:
        1. Stop idle
        2. Move to emotion expression
        3. Play audio + run lip sync in parallel
        4. Restart idle

        audio_bytes: raw WAV bytes from TTS
        """
        import pyaudio

        # Infer audio duration from WAV header
        with wave.open(io.BytesIO(audio_bytes)) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            audio_duration_ms = int((frames / rate) * 1000)
            audio_data = wf.readframes(frames)

        self.stop_idle()

        # Move to emotion expression first
        expr_name = self._emotion_to_expression(emotion)
        self.set_expression(expr_name)
        time.sleep(0.3)  # brief pause so expression registers visually

        # Launch lip sync thread
        lip_thread = threading.Thread(
            target=self.lip_sync, args=(text, audio_duration_ms), daemon=True
        )

        # Launch audio playback thread
        def play_audio():
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pa.get_format_from_width(sampwidth),
                channels=channels,
                rate=rate,
                output=True,
            )
            chunk = 1024
            offset = 0
            while offset < len(audio_data):
                stream.write(audio_data[offset : offset + chunk])
                offset += chunk
            stream.stop_stream()
            stream.close()
            pa.terminate()

        audio_thread = threading.Thread(target=play_audio, daemon=True)

        lip_thread.start()
        audio_thread.start()

        audio_thread.join()
        lip_thread.join()

        self.start_idle()


# ------------------------------------------------------------------
# Standalone test
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing expression manager (no Furby hardware — using mock).")

    class MockFurby:
        def moveTo(self, pos):
            print(f"  [mock] moveTo({pos:.1f})")

    mgr = FurbyExpressionManager(MockFurby())
    print("Starting idle for 6 seconds...")
    mgr.start_idle()
    time.sleep(6)
    mgr.stop_idle()
    print("Idle stopped.")
    print("Setting expression: happy")
    mgr.set_expression("happy")
    print("Done.")
