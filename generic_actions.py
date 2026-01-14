from typing import List


GENERIC_ACTIONS = {
    "login": [
        "로그인",
        "로그인하기",
        "로그인 하기",
        "Sign in",
        "Sign In",
        "Log in",
        "Log In",
        "Login",
    ],
    "signup": [
        "회원가입",
        "가입",
        "Sign up",
        "Sign Up",
        "Register",
        "Join",
        "Create account",
        "Create Account",
    ],
    "cart": [
        "장바구니",
        "카트",
        "Cart",
        "Basket",
        "My Cart",
    ],
    "buy": [
        "구매",
        "바로구매",
        "구매하기",
        "Buy",
        "Buy now",
        "Purchase",
    ],
    "checkout": [
        "결제",
        "결제하기",
        "주문",
        "주문하기",
        "Checkout",
        "Check out",
        "Place order",
        "Pay",
        "Pay now",
    ],
}


def _normalize(text: str) -> str:
    return text.strip().casefold()


def action_terms_for_input(text: str) -> List[str]:
    if not text or not text.strip():
        return []
    lowered = _normalize(text)
    terms: List[str] = []
    for action_terms in GENERIC_ACTIONS.values():
        for term in action_terms:
            if _normalize(term) in lowered:
                for candidate in action_terms:
                    if candidate not in terms:
                        terms.append(candidate)
                break
    return terms


def is_generic_action_input(text: str) -> bool:
    return bool(action_terms_for_input(text))
