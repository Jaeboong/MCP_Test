import shlex
from typing import Any, Dict, Optional, Tuple


KNOWN_COMMANDS = {
    "open",
    "click",
    "fill",
    "press",
    "wait",
    "scroll",
    "humanize",
    "text",
    "buttons",
    "shot",
    "start",
    "close",
    "switch",
}


def parse_command(line: str) -> Tuple[Optional[str], Dict[str, Any]]:
    parts = shlex.split(line)
    if not parts:
        return None, {}

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd not in KNOWN_COMMANDS:
        return None, {}

    if cmd == "open" and args:
        return "open_url", {"url": args[0]}
    if cmd == "click" and args:
        return "click", {"selector": args[0]}
    if cmd == "fill" and len(args) >= 2:
        return "fill", {"selector": args[0], "text": " ".join(args[1:])}
    if cmd == "press" and len(args) >= 2:
        return "press", {"selector": args[0], "key": args[1]}
    if cmd == "wait" and args:
        return "wait", {"ms": int(args[0])}
    if cmd == "scroll" and args:
        return "scroll", {"delta_y": int(args[0])}
    if cmd == "humanize":
        steps = int(args[0]) if args else 3
        return "humanize", {"steps": steps}
    if cmd == "text":
        max_chars = int(args[0]) if args else 2000
        return "get_text", {"max_chars": max_chars}
    if cmd == "buttons":
        max_items = int(args[0]) if args else 200
        return "get_visible_buttons", {"max_items": max_items}
    if cmd == "shot" and args:
        return "screenshot", {"path": args[0], "full_page": True}
    if cmd == "start":
        headless = bool(args and args[0].lower() == "headless")
        return "start_browser", {"headless": headless}
    if cmd == "close":
        return "close_browser", {}
    if cmd == "switch":
        return "switch_latest_page", {}

    return None, {}


def print_help() -> None:
    print("Commands:")
    print("  start [headless]")
    print("  open <url>")
    print("  click <selector>")
    print("  fill <selector> <text>")
    print("  press <selector> <key>")
    print("  wait <ms>")
    print("  scroll <pixels>")
    print("  humanize [steps]")
    print("  text [max_chars]")
    print("  buttons [max_items]")
    print("  shot <path>")
    print("  switch")
    print("  close")
    print("  exit | quit")
