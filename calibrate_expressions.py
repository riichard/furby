#!/usr/bin/env python3
"""
calibrate_expressions.py — Interactive CLI to map dial positions to expression names.

Usage:
    python calibrate_expressions.py

Commands:
    <number>    Move to position 0–100
    +           Fine-tune +1
    -           Fine-tune -1
    save NAME   Save current position as expression NAME
    list        Show all saved expressions
    write       Write saved expressions to config/expressions.yaml
    quit        Exit without writing
"""

import os
import sys
import yaml

CONFIG_PATH = "config/expressions.yaml"


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


def write_config(config):
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    print(f"[calibrate] Written to {CONFIG_PATH}")


def print_help():
    print("""
Commands:
  <number>   Move to position (0–100)
  +          Fine-tune +1
  -          Fine-tune -1
  save NAME  Save current position as expression NAME
  list       Show saved expressions
  write      Write to config/expressions.yaml
  quit       Exit
""")


def main():
    # Import Furby — gracefully handle missing GPIO on non-Pi hardware
    try:
        from furby import Furby
        furby = Furby()
        print("[calibrate] Calibrating hardware...")
        furby.calibrate()
        print("[calibrate] Calibration complete.")
        use_hardware = True
    except Exception as e:
        print(f"[calibrate] WARNING: Could not initialize Furby hardware ({e}).")
        print("[calibrate] Running in simulation mode (no motor movement).")
        use_hardware = False
        class MockFurby:
            def moveTo(self, pos):
                print(f"  [mock] moveTo({pos})")
        furby = MockFurby()

    config = load_config()
    if "expressions" not in config:
        config["expressions"] = {}

    current_pos = 50
    furby.moveTo(current_pos)
    print(f"\nFurby Expression Calibration Tool")
    print(f"Current position: {current_pos}")
    print_help()

    while True:
        try:
            raw = input(f"[pos={current_pos}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[calibrate] Exiting.")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "quit":
            print("[calibrate] Exiting without writing.")
            break

        elif cmd == "write":
            write_config(config)

        elif cmd == "list":
            exprs = config.get("expressions", {})
            if not exprs:
                print("  (no saved expressions)")
            else:
                print("  Saved expressions:")
                for name, data in sorted(exprs.items()):
                    desc = data.get("description", "")
                    print(f"    {name:20s} position={data['position']:5}  {desc}")

        elif cmd == "save":
            if len(parts) < 2:
                print("  Usage: save NAME")
                continue
            name = parts[1].lower()
            desc = " ".join(parts[2:]) if len(parts) > 2 else ""
            config["expressions"][name] = {
                "position": current_pos,
                "description": desc,
            }
            print(f"  Saved {name!r} = position {current_pos}")

        elif cmd == "+":
            current_pos = min(100, current_pos + 1)
            furby.moveTo(current_pos)
            print(f"  Position: {current_pos}")

        elif cmd == "-":
            current_pos = max(0, current_pos - 1)
            furby.moveTo(current_pos)
            print(f"  Position: {current_pos}")

        else:
            try:
                pos = int(cmd)
                if not 0 <= pos <= 100:
                    print("  Position must be 0–100.")
                    continue
                current_pos = pos
                furby.moveTo(current_pos)
                print(f"  Moved to position {current_pos}")
            except ValueError:
                print(f"  Unknown command: {raw!r}")
                print_help()

    # Cleanup GPIO if hardware was used
    if use_hardware:
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()
