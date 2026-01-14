from __future__ import annotations

import re
from urllib.parse import quote


def naver_shopping_search_url(query: str) -> str:
    q = query.strip()
    return f"https://search.shopping.naver.com/ns/search?query={quote(q)}"


def is_naver_shopping(url: str) -> bool:
    return "shopping.naver.com" in url or "search.shopping.naver.com" in url


def naver_rule_commands(user_text: str) -> list[tuple[str, dict[str, str]]]:
    text = user_text.strip()
    if not text:
        return []

    if ("네이버" in text and "쇼핑" in text and "검색" in text) or ("네이버" in text and "검색" in text):
        match = re.search(r"네이버(?:\\s*쇼핑)?(?:에|에서)?\\s*(.+?)\\s*검색", text)
        query = match.group(1) if match else text.replace("네이버", "").replace("쇼핑", "").replace("검색", "").strip()
        if query:
            return [
                ("start_browser", {"headless": False}),
                ("open_url", {"url": naver_shopping_search_url(query)}),
                ("wait", {"ms": 800}),
            ]

    return []
