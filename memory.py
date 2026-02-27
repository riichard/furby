#!/usr/bin/env python3
"""MemoryManager: persistent conversation log and long-term memory for Furby."""

import json
import os
from datetime import datetime, timezone

SUMMARY_THRESHOLD = 50  # trigger summarize after this many new turns in a session


class MemoryManager:
    def __init__(self, memory_dir="memory"):
        self.memory_dir = memory_dir
        self.log_path = os.path.join(memory_dir, "conversations.jsonl")
        self.long_term_path = os.path.join(memory_dir, "long_term.md")
        os.makedirs(memory_dir, exist_ok=True)
        self._new_turns = 0  # turns logged this session

    def load_context(self) -> str:
        """Return contents of long_term.md, or empty string if not yet created."""
        try:
            with open(self.long_term_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return ""

    def log_turn(self, user: str, furby: str, emotion: str):
        """Append one conversation turn to conversations.jsonl."""
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "user": user,
            "furby": furby,
            "emotion": emotion,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        self._new_turns += 1

    def should_summarize(self) -> bool:
        """True if enough new turns have accumulated this session to warrant a summary."""
        return self._new_turns >= SUMMARY_THRESHOLD

    def summarize(self):
        """Regenerate long_term.md from conversations.jsonl using Claude."""
        from summarize import run_summarize
        run_summarize(self.memory_dir)
        self._new_turns = 0
