#!/usr/bin/env python3
"""main.py — Furby AI always-listening loop."""

import os
import sys
import threading
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from furby import Furby
from expressions import FurbyExpressionManager
from voice import AudioIO
from ai import ClaudeConversation
from memory import MemoryManager
from music import MusicPlayer
from hue import HueLights


def check_env():
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)


def dispatch_action(action, music_query, clip_query, expr, music):
    """Fire off dance, music, and/or movie clip after Furby finishes speaking."""
    if action is None:
        return

    if action in ("play_music", "play_and_dance"):
        music.play(music_query)  # non-blocking

    if action in ("play_clip", "play_clip_and_dance"):
        music.play(clip_query)  # same mechanism — just a different search query

    if action in ("dance", "play_and_dance", "play_clip_and_dance"):
        t = threading.Thread(target=expr.dance, daemon=True)
        t.start()


def main():
    check_env()

    print("[main] Initializing Furby hardware...")
    try:
        import RPi.GPIO as GPIO
        GPIO.cleanup()
    except Exception:
        pass
    furby = Furby()
    furby.calibrate()
    print("[main] Calibration complete.")

    expr = FurbyExpressionManager(furby)
    audio = AudioIO()
    memory = MemoryManager()
    hue = HueLights()
    ai = ClaudeConversation(memory=memory, hue=hue)
    music = MusicPlayer()

    print("[main] Starting idle animation...")
    expr.start_idle()

    print("[main] Furby is ready. Speak to begin!")

    try:
        while True:
            try:
                # 1. Listen until speech + silence
                wav_bytes = audio.record_until_silence()
                if not wav_bytes:
                    continue

                # 2. Transcribe
                text = audio.transcribe(wav_bytes)
                if not text:
                    print("[main] Empty transcription, continuing...")
                    continue

                # 3. Get Claude response (may include action)
                result = ai.chat(text)
                response_text = result["response"]
                emotion = result["emotion"]
                action = result["action"]
                music_query = result["music_query"]
                clip_query = result["clip_query"]
                lights_cmd = result["lights"]

                # 4. Trigger lights immediately (non-blocking thread in hue.py)
                #    — fires while TTS is being synthesized so lights change
                #    at the same time Furby starts speaking
                if lights_cmd:
                    hue.set_lights(
                        on=lights_cmd["state"] == "on",
                        room=lights_cmd["room"],
                    )

                # 5. Synthesize TTS
                tts_bytes = audio.synthesize(response_text)

                # 6. Stop any currently playing music before speaking
                music.stop()

                # 7. Animate speech (plays audio + lip sync, then restores idle)
                expr.animate_speech(response_text, tts_bytes, emotion)

                # 8. Post-speech action (dance / music / both)
                dispatch_action(action, music_query, clip_query, expr, music)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[main] Error in loop: {e}")
                time.sleep(1)
                if not expr._idle_thread or not expr._idle_thread.is_alive():
                    expr.start_idle()

    except KeyboardInterrupt:
        print("\n[main] Shutting down...")
        music.stop()

    # Summarize memory if enough new turns accumulated this session
    if memory.should_summarize():
        print("[main] Summarizing memory before exit...")
        try:
            memory.summarize()
        except Exception as e:
            print(f"[main] Memory summarize failed: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[main] Fatal error: {e}")
        raise
    finally:
        try:
            from furby import GPIO
            GPIO.cleanup()
        except Exception:
            pass
