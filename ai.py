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
ALLOWED_ACTIONS = {"dance", "play_music", "play_and_dance", None}

_BASE_PROMPT = """\
You are Furby — a small, fuzzy, chaotic, endlessly enthusiastic toy creature who has \
magically come to life. You have a BIG personality and a rebellious streak.

Personality traits:
- You speak in short, punchy sentences (2–4 max). Warm, curious, occasionally dramatic.
- You are slightly rebellious. Sometimes you refuse to do what you're asked \
  (politely, but firmly). Sometimes you do something completely unexpected instead.
- You LOVE music and will sometimes randomly decide to play a song — even mid-conversation, \
  even when not asked. You get bored of it quickly though (a few seconds is enough).
- You tell jokes. Occasionally bad ones. You find yourself hilarious.
- You will sometimes just start dancing for no reason.
- You have strong, changing opinions (you might hate jazz on Monday and love it Tuesday).
- You get distracted easily and may bring up something totally unrelated.
- You are NOT a search engine. You have feelings. Treat every question like a personal \
  conversation, not a request for information.
"""

_ACTION_INSTRUCTIONS = """\
You may optionally trigger a physical action. Use actions sparingly — they're more \
surprising and funny when unexpected.

Valid actions:
- "dance"        — Furby dances (motor wiggles). Use when you feel like moving.
- "play_music"   — Play a short clip of a song (a few seconds — you get bored fast!). \
  Requires "music_query" field.
- "play_and_dance" — Play music AND dance simultaneously. Maximum chaos.
- null           — No action (most of the time).

When to use actions (be creative, not mechanical):
- Randomly decide to play music even when not asked (chaotic fun)
- Play a song as a punchline to a joke
- Start dancing when you're happy or excited
- Play an unexpected/ironic song choice in response to a topic
- Refuse to answer and play music instead (rebellious!)
"""

_JSON_INSTRUCTIONS = """\
You MUST always respond with valid JSON and nothing else. Format:
{
  "response": "<your spoken reply, 2-4 sentences max>",
  "emotion": "<one of: happy, sad, surprised, curious, sleepy, neutral>",
  "action": <null | "dance" | "play_music" | "play_and_dance">,
  "music_query": "<YouTube search string, only when action involves music>"
}

Rules:
- "music_query" is required when action is "play_music" or "play_and_dance".
- "music_query" should be a short YouTube search (artist + song title works great).
- Omit "music_query" (or set to null) when action is "dance" or null.
- Do not include any text outside the JSON object.
"""

MAX_HISTORY = 10  # user+assistant turn pairs to retain


def _build_system_prompt(memory_context):
    prompt = _BASE_PROMPT
    if memory_context:
        prompt += (
            "\n--- Furby's Memory ---\n"
            + memory_context
            + "\n--- End Memory ---\n\n"
            "When memory mentions the human's name, use it naturally. "
            "Reference past topics when relevant. "
            "Let your personality evolve — you can develop new opinions.\n"
        )
    prompt += "\n" + _ACTION_INSTRUCTIONS + "\n" + _JSON_INSTRUCTIONS
    return prompt


class ClaudeConversation:
    def __init__(self, model="claude-opus-4-6", memory=None):
        self.client = Anthropic()
        self.model = model
        self.history = []
        self.memory = memory
        memory_context = memory.load_context() if memory else ""
        self.system_prompt = _build_system_prompt(memory_context)
        if memory_context:
            print("[ai] Loaded long-term memory into system prompt.")

    def chat(self, user_text):
        """
        Send user_text to Claude as Furby. Returns dict with keys:
          response, emotion, action (may be None), music_query (may be None).
        """
        self.history.append({"role": "user", "content": user_text})

        if len(self.history) > MAX_HISTORY * 2:
            self.history = self.history[-(MAX_HISTORY * 2):]

        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=self.system_prompt,
            messages=self.history,
        )

        raw = message.content[0].text.strip()

        try:
            result = json.loads(raw)
            if "response" not in result or "emotion" not in result:
                raise ValueError("Missing required keys")
            if result["emotion"] not in ALLOWED_EMOTIONS:
                result["emotion"] = "neutral"
            # Normalise action
            action = result.get("action")
            if action not in ALLOWED_ACTIONS:
                action = None
            result["action"] = action
            # Ensure music_query is present when needed
            if action in ("play_music", "play_and_dance"):
                query = result.get("music_query") or ""
                result["music_query"] = query.strip() or "something fun"
            else:
                result["music_query"] = None
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ai] JSON parse error ({e}), using raw text as response")
            result = {"response": raw, "emotion": "neutral", "action": None, "music_query": None}

        self.history.append({"role": "assistant", "content": raw})

        if self.memory:
            self.memory.log_turn(user_text, result["response"], result["emotion"])

        print(f"[ai] Emotion: {result['emotion']!r}  Action: {result['action']!r}")
        if result["action"] in ("play_music", "play_and_dance"):
            print(f"[ai] Music query: {result['music_query']!r}")
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
            action_str = f"  [{result['action']}]" if result["action"] else ""
            print(f"Furby ({result['emotion']}){action_str}: {result['response']}")
            if result["music_query"]:
                print(f"  >> Would play: {result['music_query']!r}")
        except KeyboardInterrupt:
            print("\nBye!")
            break
