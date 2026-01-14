from __future__ import annotations

from urllib.parse import quote


def naver_shopping_search_url(query: str) -> str:
    q = query.strip()
    return f"https://search.shopping.naver.com/ns/search?query={quote(q)}"


def is_naver_shopping(url: str) -> bool:
    return "shopping.naver.com" in url or "search.shopping.naver.com" in url
