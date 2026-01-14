from __future__ import annotations


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
