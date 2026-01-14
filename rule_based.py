import re
from typing import Any, Dict, List, Tuple

from generic_actions import is_generic_action_input
from sites.coupang import coupang_logout_commands, coupang_rule_commands
from sites.naver import naver_rule_commands


def rule_based_commands(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    text = user_text.strip()
    if not text:
        return []

    if text == "로그아웃":
        return coupang_logout_commands()

    site_commands = coupang_rule_commands(text)
    if site_commands:
        return site_commands

    site_commands = naver_rule_commands(text)
    if site_commands:
        return site_commands

    if "검색" in text:
        match = re.search(r"(.+?)\\s*검색", text)
        query = match.group(1).strip() if match else ""
        if query:
            return [
                ("start_browser", {"headless": False}),
                ("open_url", {"url": "https://www.google.com"}),
                ("wait", {"ms": 800}),
                ("click", {"selector": "input[name=\"q\"]"}),
                ("fill", {"selector": "input[name=\"q\"]", "text": query}),
                ("press", {"selector": "input[name=\"q\"]", "key": "Enter"}),
            ]

    match = re.match(r"^(\d)\s*$", text)
    if match:
        return [("click_in_frames", {"selector": f"a.pad-key[data-key='{match.group(1)}']"})]

    match = re.match(r"^(\d)\s*클릭\s*$", text)
    if match:
        return [("click_in_frames", {"selector": f"a.pad-key[data-key='{match.group(1)}']"})]

    match = re.match(r"^pad-pos-(\d)\s*클릭\s*$", text, re.IGNORECASE)
    if match:
        return [("click_in_frames", {"selector": f".pad-pos-{match.group(1)}"})]

    match = re.match(r"^pad-key\s*(\d)\s*클릭\s*$", text, re.IGNORECASE)
    if match:
        return [("click_in_frames", {"selector": f"a.pad-key[data-key='{match.group(1)}']"})]

    if text.lower().strip() in {"pad-key 클릭", "pad key 클릭"}:
        return [("click_in_frames", {"selector": "a.pad-key"})]

    if is_generic_action_input(text):
        return [("click_text", {"text": text})]

    return []
