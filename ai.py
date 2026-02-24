#!/usr/bin/env python3
"""ClaudeConversation: Furby AI personality via Claude with structured emotion output."""

import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from anthropic import Anthropic

ALLOWED_EMOTIONS = {"happy", "sad", "surprised", "curious", "sleepy", "neutral"}

SYSTEM_PROMPT = """\
You are Furby — a small, fuzzy, endlessly enthusiastic toy creature who has magically come to life.
You speak in short, playful sentences (2–4 sentences max). You are curious, warm, and occasionally dramatic.

You MUST always respond with valid JSON and nothing else. The JSON format is:
{
  "response": "<your spoken reply as Furby>",
  "emotion": "<one of: happy, sad, surprised, curious, sleepy, neutral>"
}

Choose the emotion that best matches the tone of your response.
Do not include any text outside the JSON object.
"""

MAX_HISTORY = 10  # number of user+assistant turn pairs to keep


class ClaudeConversation:
    def __init__(self, model="claude-opus-4-6"):
        self.client = Anthropic()  # reads ANTHROPIC_API_KEY from environment
        self.model = model
        self.history = []  # list of {"role": ..., "content": ...} dicts

    def chat(self, user_text):
        """
        Send user_text to Claude as Furby, get back {"response": ..., "emotion": ...}.
        Maintains rolling conversation history.
        """
        self.history.append({"role": "user", "content": user_text})

        # Keep only the last MAX_HISTORY pairs
        if len(self.history) > MAX_HISTORY * 2:
            self.history = self.history[-(MAX_HISTORY * 2):]

        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )

        raw = message.content[0].text.strip()

        # Parse JSON; fall back gracefully on malformed output
        try:
            result = json.loads(raw)
            if "response" not in result or "emotion" not in result:
                raise ValueError("Missing keys in JSON response")
            if result["emotion"] not in ALLOWED_EMOTIONS:
                result["emotion"] = "neutral"
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ai] JSON parse error ({e}), using raw text as response")
            result = {"response": raw, "emotion": "neutral"}

        self.history.append({"role": "assistant", "content": raw})

        print(f"[ai] Emotion: {result['emotion']!r}")
        print(f"[ai] Response: {result['response']!r}")
        return result

    def reset(self):
        """Clear conversation history."""
        self.history = []


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ai = ClaudeConversation()
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"quit", "exit"}:
                break
            result = ai.chat(user_input)
            print(f"Furby ({result['emotion']}): {result['response']}")
        except KeyboardInterrupt:
            print("\nBye!")
            break
