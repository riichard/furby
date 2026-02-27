#!/usr/bin/env python3
"""main.py — Furby AI always-listening loop."""

import os
import sys
import time

# Load .env if present (optional convenience)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from furby import Furby
from expressions import FurbyExpressionManager
from voice import AudioIO
from ai import ClaudeConversation


def check_env():
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)


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
    ai = ClaudeConversation()

    print("[main] Starting idle animation...")
    expr.start_idle()

    print("[main] Furby is ready. Speak to begin!")

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

            # 3. Get Claude response with emotion
            result = ai.chat(text)
            response_text = result["response"]
            emotion = result["emotion"]

            # 4. Synthesize TTS
            tts_bytes = audio.synthesize(response_text)

            # 5. Animate speech (plays audio + lip sync, then restores idle)
            expr.animate_speech(response_text, tts_bytes, emotion)

        except KeyboardInterrupt:
            print("\n[main] Shutting down...")
            break
        except Exception as e:
            print(f"[main] Error in loop: {e}")
            time.sleep(1)
            # Ensure idle keeps running after any error
            if not expr._idle_thread or not expr._idle_thread.is_alive():
                expr.start_idle()


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
