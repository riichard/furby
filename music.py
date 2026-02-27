#!/usr/bin/env python3
"""MusicPlayer: search YouTube and play brief clips through Furby's speaker.

Uses yt-dlp to get a stream URL and ffplay to output audio.
Clips are intentionally short — Furby gets bored fast.
"""

import random
import subprocess
import threading

# How long Furby will tolerate playing music before losing interest (seconds)
PLAY_DURATION_RANGE = (3, 8)


class MusicPlayer:
    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()

    def play(self, query, duration_s=None):
        """Search for query and play for a few seconds. Non-blocking."""
        if duration_s is None:
            duration_s = random.uniform(*PLAY_DURATION_RANGE)
        t = threading.Thread(
            target=self._play_thread, args=(query, duration_s), daemon=True
        )
        t.start()
        return t

    def _play_thread(self, query, duration_s):
        self.stop()  # kill any current playback first
        print(f"[music] Searching: {query!r} (will play ~{duration_s:.1f}s)")
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    f"ytsearch1:{query}",
                    "--get-url",
                    "--format", "bestaudio/best",
                    "--no-playlist",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            url = result.stdout.strip().split("\n")[0]
            if not url:
                print("[music] No URL found — giving up.")
                return

            print(f"[music] Got URL, starting playback...")
            with self._lock:
                self._proc = subprocess.Popen(
                    [
                        "ffplay",
                        "-nodisp",
                        "-autoexit",
                        "-loglevel", "quiet",
                        "-t", str(duration_s),
                        url,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            self._proc.wait()
            print("[music] Clip finished.")
        except subprocess.TimeoutExpired:
            print("[music] Search timed out.")
        except FileNotFoundError as e:
            print(f"[music] Missing dependency: {e}. Run: sudo apt install ffmpeg && pip3 install yt-dlp")
        except Exception as e:
            print(f"[music] Error: {e}")
        finally:
            with self._lock:
                self._proc = None

    def stop(self):
        """Cut the music immediately."""
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                self._proc = None
