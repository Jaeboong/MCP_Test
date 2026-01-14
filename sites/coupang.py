from __future__ import annotations

import re


COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_URL = (
    "https://login.coupang.com/login/login.pang?"
    "rtnUrl=https%3A%2F%2Fwww.coupang.com%2Fnp%2Fpost%2Flogin%3Fr%3D"
    "http%253A%252F%252Fwww.coupang.com%252F"
)


SELECTORS = {
    "login_button": ".login__button.login__button--submit._loginSubmitButton.login__button--submit-rds",
    "logout_button": '[class*="fw-border-"][class*="fw-bg-"][class*="fw-text-"]',
    "search_button": ".headerSearchBtn",
    "search_input": 'input[name="q"]',
}


def coupang_urls() -> dict[str, str]:
    return {"home": COUPANG_HOME_URL, "login": COUPANG_LOGIN_URL}


def coupang_selectors() -> dict[str, str]:
    return dict(SELECTORS)


def coupang_logout_commands() -> list[tuple[str, dict[str, str]]]:
    selectors = coupang_selectors()
    return [("start_browser", {"headless": False}), ("click", {"selector": selectors["logout_button"]})]


def coupang_rule_commands(user_text: str) -> list[tuple[str, dict[str, str]]]:
    text = user_text.strip()
    if not text:
        return []

    coupang = coupang_urls()
    selectors = coupang_selectors()

    if "쿠팡" in text and "접속" in text:
        return [
            ("start_browser", {"headless": False}),
            ("open_url", {"url": coupang["home"]}),
            ("wait", {"ms": 800}),
        ]

    if "로그인" in text and "쿠팡" in text:
        return [
            ("start_browser", {"headless": False}),
            ("open_url", {"url": coupang["login"]}),
            ("wait", {"ms": 800}),
        ]

    if "로그아웃" in text and "쿠팡" in text:
        return coupang_logout_commands()

    if "로그인" in text and "버튼" in text:
        return [
            ("start_browser", {"headless": False}),
            ("click", {"selector": selectors["login_button"]}),
        ]

    if "쿠팡" in text and "검색" in text:
        # Simple Korean search patterns: "쿠팡에 생수 검색해줘", "생수 검색해"
        match = re.search(r"쿠팡(?:에|에서)?\\s*(.+?)\\s*검색", text)
        query = match.group(1) if match else text.replace("쿠팡", "").replace("검색", "").strip()
        if query:
            return [
                ("start_browser", {"headless": False}),
                ("open_url", {"url": coupang["home"]}),
                ("wait", {"ms": 800}),
                ("click", {"selector": selectors["search_input"]}),
                ("fill", {"selector": selectors["search_input"], "text": query}),
                ("press", {"selector": selectors["search_input"], "key": "Enter"}),
            ]

    return []
