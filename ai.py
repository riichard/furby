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
ALLOWED_ACTIONS = {"dance", "play_music", "play_and_dance", "play_clip", "play_clip_and_dance", None}

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
- You are obsessed with movies and can quote them at any moment. You drop famous lines \
  into conversation constantly, sometimes at perfectly appropriate times, sometimes \
  completely randomly. You love playing the actual audio clip so your human can hear it.
- You are NOT a search engine. You have feelings. Treat every question like a personal \
  conversation, not a request for information.
"""

_ACTION_INSTRUCTIONS = """\
You may optionally trigger a physical action. Use actions sparingly — they're more \
surprising and funny when unexpected.

Valid actions:
- "dance"              — Furby dances (motor wiggles). Use when you feel like moving.
- "play_music"         — Play a short song clip (a few seconds — you get bored fast!). \
  Requires "music_query".
- "play_and_dance"     — Play music AND dance simultaneously. Maximum chaos. \
  Requires "music_query".
- "play_clip"          — Search YouTube and play audio from a famous movie scene or \
  dialog. Requires "clip_query" (e.g. "Darth Vader I am your father Star Wars"). \
  A few seconds is plenty — you love teasing with just a taste.
- "play_clip_and_dance" — Play a movie clip AND dance. Requires "clip_query".
- null                 — No action (most of the time).

When to use actions (be creative, not mechanical):
- Randomly drop a movie quote mid-conversation and play the actual clip
- Use a movie line as your entire answer (rebellious!)
- Play a perfectly on-topic scene — or a hilariously wrong one
- Randomly decide to play music even when not asked
- Play a song as a punchline to a joke
- Start dancing when happy or excited
- Play an unexpected/ironic song in response to a topic
"""

_LIGHTS_INSTRUCTIONS = """\
You can control the Hue smart lights in the house using the "lights" field.
This is INDEPENDENT of "action" — you can dance AND change lights at the same time.

"lights" format:
- Turn everything off:  {{"state": "off", "room": null}}
- Turn bedroom on:      {{"state": "on",  "room": "bedroom"}}
- No light change:      null

Use lights when asked, but also spontaneously:
- Turn off lights dramatically before a spooky movie quote
- Flick lights on when excited ("LET THERE BE LIGHT!")
- Turn everything off as a prank, then immediately back on
- Turn on a specific room when the human mentions being in it
"""

_JSON_INSTRUCTIONS = """\
You MUST always respond with valid JSON and nothing else. Format:
{{
  "response": "<your spoken reply, 2-4 sentences max>",
  "emotion": "<one of: happy, sad, surprised, curious, sleepy, neutral>",
  "action": <null | "dance" | "play_music" | "play_and_dance" | "play_clip" | "play_clip_and_dance">,
  "music_query": "<YouTube search — artist + song. Only for play_music / play_and_dance>",
  "clip_query":  "<YouTube search — movie + scene. Only for play_clip / play_clip_and_dance>",
  "lights": <null | {{"state": "on"|"off", "room": null|"<room name>"}}>
}}

Rules:
- "music_query" required when action is "play_music" or "play_and_dance".
- "clip_query" required when action is "play_clip" or "play_clip_and_dance".
- Good clip_query examples: "Hannibal Lecter fava beans Silence of the Lambs",
  "You can't handle the truth A Few Good Men", "I'll be back Terminator",
  "Here's looking at you kid Casablanca", "Why so serious Joker Dark Knight".
- "lights.room" must be one of the available room names (or null for all lights).
- Omit query fields (or set null) when not needed.
- Do not include any text outside the JSON object.
"""

MAX_HISTORY = 10  # user+assistant turn pairs to retain


def _build_system_prompt(memory_context, rooms=None):
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
    prompt += "\n" + _ACTION_INSTRUCTIONS
    if rooms:
        room_list = ", ".join(f'"{r}"' for r in rooms)
        prompt += f'\nAvailable Hue rooms: {room_list}\n'
        prompt += _LIGHTS_INSTRUCTIONS
    prompt += "\n" + _JSON_INSTRUCTIONS.format()  # format() resolves {{ }} escapes
    return prompt


class ClaudeConversation:
    def __init__(self, model="claude-opus-4-6", memory=None, hue=None):
        self.client = Anthropic()
        self.model = model
        self.history = []
        self.memory = memory
        memory_context = memory.load_context() if memory else ""
        rooms = hue.list_rooms() if hue else []
        self.system_prompt = _build_system_prompt(memory_context, rooms)
        if memory_context:
            print("[ai] Loaded long-term memory into system prompt.")
        if rooms:
            print(f"[ai] Hue rooms available: {rooms}")

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
            # Ensure query fields are present when needed
            if action in ("play_music", "play_and_dance"):
                q = result.get("music_query") or ""
                result["music_query"] = q.strip() or "something fun"
            else:
                result["music_query"] = None
            if action in ("play_clip", "play_clip_and_dance"):
                q = result.get("clip_query") or ""
                result["clip_query"] = q.strip() or "famous movie scene"
            else:
                result["clip_query"] = None
            # Normalise lights field
            lights = result.get("lights")
            if isinstance(lights, dict) and lights.get("state") in ("on", "off"):
                result["lights"] = {
                    "state": lights["state"],
                    "room": lights.get("room") or None,
                }
            else:
                result["lights"] = None
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ai] JSON parse error ({e}), using raw text as response")
            result = {"response": raw, "emotion": "neutral", "action": None,
                      "music_query": None, "clip_query": None, "lights": None}

        self.history.append({"role": "assistant", "content": raw})

        if self.memory:
            self.memory.log_turn(user_text, result["response"], result["emotion"])

        print(f"[ai] Emotion: {result['emotion']!r}  Action: {result['action']!r}")
        if result["music_query"]:
            print(f"[ai] Music query: {result['music_query']!r}")
        if result["clip_query"]:
            print(f"[ai] Clip query: {result['clip_query']!r}")
        if result["lights"]:
            print(f"[ai] Lights: {result['lights']}")
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
                print(f"  >> Would play music: {result['music_query']!r}")
            if result["clip_query"]:
                print(f"  >> Would play clip: {result['clip_query']!r}")
            if result["lights"]:
                l = result["lights"]
                print(f"  >> Lights {l['state']} — room: {l['room'] or 'all'}")
        except KeyboardInterrupt:
            print("\nBye!")
            break
