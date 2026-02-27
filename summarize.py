#!/usr/bin/env python3
"""Compress Furby's conversation log into long_term.md.

Safe to run at any time — from cron or manually.
Reads conversations.jsonl, calls Claude to update long_term.md,
then appends a summarization marker to the log.

Usage:
  python3 summarize.py [--memory-dir memory]
"""

import json
import os
import sys
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from anthropic import Anthropic

SUMMARIZE_SYSTEM = """\
You are maintaining Furby's long-term memory. Furby is a small, fuzzy, endlessly \
enthusiastic toy creature who has magically come to life.

Given the recent conversations and the existing memory document, update the memory \
document to reflect new facts, topics, and personality traits.

Guidelines:
- Keep the document under 800 words.
- Write warmly in first person from Furby's perspective.
- Capture the human's name and personal details when mentioned.
- Record opinions and preferences Furby has expressed.
- Note recurring topics and memorable moments.
- Track approximately how many conversations have happened.
- Include a "Current Mood" line based on the most recent exchanges.

Return ONLY the updated memory document — no preamble, no explanation.\
"""


def run_summarize(memory_dir: str = "memory"):
    log_path = os.path.join(memory_dir, "conversations.jsonl")
    long_term_path = os.path.join(memory_dir, "long_term.md")

    if not os.path.exists(log_path):
        print(f"[summarize] No conversation log at {log_path}, nothing to do.")
        return

    # Read all unsummarized conversation turns
    turns = []
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("# summarized"):
                continue
            try:
                turns.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not turns:
        print("[summarize] No conversation turns found, nothing to do.")
        return

    # Format turns for the prompt
    formatted = []
    for t in turns:
        formatted.append(f"[{t['ts']}] Human: {t['user']}")
        formatted.append(f"[{t['ts']}] Furby ({t['emotion']}): {t['furby']}")
    conversations_text = "\n".join(formatted)

    # Read existing long_term.md if present
    existing_memory = ""
    try:
        with open(long_term_path, "r") as f:
            existing_memory = f.read().strip()
    except FileNotFoundError:
        pass

    user_message = (
        "## Existing Memory Document\n"
        + (existing_memory if existing_memory else "(none yet — this is the first summary)")
        + "\n\n## Recent Conversations\n"
        + conversations_text
    )

    client = Anthropic()
    print(f"[summarize] Summarizing {len(turns)} turns...")

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SUMMARIZE_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )

    new_memory = response.content[0].text.strip()

    with open(long_term_path, "w") as f:
        f.write(new_memory + "\n")
    print(f"[summarize] Wrote {long_term_path} ({len(new_memory)} chars).")

    # Mark the log so we don't re-summarize these turns
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"# summarized up to {ts}\n")
    print(f"[summarize] Marked log as summarized at {ts}.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Summarize Furby's conversation log.")
    parser.add_argument("--memory-dir", default="memory", help="Path to memory directory")
    args = parser.parse_args()
    run_summarize(args.memory_dir)
