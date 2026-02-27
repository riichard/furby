#!/usr/bin/env python3
"""HueLights: control Philips Hue lights via the local bridge API.

Requires:  pip3 install phue
Config:    HUE_BRIDGE_IP=192.168.x.x  in .env (or environment)

First-run pairing: press the button on the Hue bridge, then start Furby.
Credentials are saved automatically to ~/.python_hue by phue.
"""

import os
import threading

try:
    from phue import Bridge, PhueRegistrationException
    _PHUE_OK = True
except ImportError:
    _PHUE_OK = False


class HueLights:
    def __init__(self, bridge_ip=None):
        self.bridge = None
        self._lock = threading.Lock()

        if not _PHUE_OK:
            print("[hue] phue not installed — lights disabled. Run: pip3 install phue")
            return

        ip = bridge_ip or os.getenv("HUE_BRIDGE_IP", "").strip()
        if not ip:
            print("[hue] HUE_BRIDGE_IP not set — lights disabled.")
            return

        try:
            self.bridge = Bridge(ip)
            self.bridge.connect()
            rooms = self.list_rooms()
            print(f"[hue] Connected to bridge at {ip}. Rooms: {rooms}")
        except PhueRegistrationException:
            print("[hue] Bridge not paired. Press the button on the Hue bridge and restart.")
            self.bridge = None
        except Exception as e:
            print(f"[hue] Could not connect to bridge at {ip}: {e}")
            self.bridge = None

    @property
    def available(self):
        return self.bridge is not None

    def list_rooms(self):
        """Return names of all rooms and zones from the bridge."""
        if not self.available:
            return []
        try:
            groups = self.bridge.get_group()
            return [
                g["name"] for g in groups.values()
                if g.get("type") in ("Room", "Zone")
            ]
        except Exception:
            return []

    def _find_group_id(self, room_name):
        """Case-insensitive substring match to find a Hue group ID."""
        try:
            groups = self.bridge.get_group()
            target = room_name.lower()
            for gid, g in groups.items():
                name = g["name"].lower()
                if target in name or name in target:
                    return int(gid)
        except Exception:
            pass
        return None

    def set_lights(self, on, room=None):
        """Turn lights on or off. room=None affects every light in the house."""
        if not self.available:
            print("[hue] Not connected — ignoring light command.")
            return

        state_str = "ON" if on else "OFF"

        def _do():
            with self._lock:
                try:
                    if room:
                        gid = self._find_group_id(room)
                        if gid is not None:
                            self.bridge.set_group(gid, "on", on)
                            print(f"[hue] {room!r} → {state_str}")
                            return
                        print(f"[hue] Room {room!r} not found — controlling all lights")
                    # All lights
                    ids = [l.light_id for l in self.bridge.lights]
                    if ids:
                        self.bridge.set_light(ids, "on", on)
                        print(f"[hue] All lights → {state_str}")
                except Exception as e:
                    print(f"[hue] set_lights error: {e}")

        threading.Thread(target=_do, daemon=True).start()
