from urllib.parse import urlparse

from generic_actions import is_generic_action_input


SHOPPING_HOSTS = {
    "coupang.com",
    "www.coupang.com",
    "search.shopping.naver.com",
    "shopping.naver.com",
    "11st.co.kr",
    "www.11st.co.kr",
    "gmarket.co.kr",
    "www.gmarket.co.kr",
    "auction.co.kr",
    "www.auction.co.kr",
    "ssg.com",
    "www.ssg.com",
    "wemakeprice.com",
    "www.wemakeprice.com",
    "tmon.co.kr",
    "www.tmon.co.kr",
    "interpark.com",
    "shopping.interpark.com",
}


def _host_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_shopping_site(url: str) -> bool:
    host = _host_from_url(url)
    if not host:
        return False
    if host in SHOPPING_HOSTS:
        return True
    return host.endswith(".coupang.com")


def should_click_search_result(user_text: str, last_url: str) -> bool:
    text = user_text.strip()
    if not text:
        return False
    if not is_shopping_site(last_url):
        return False
    lowered = text.casefold()
    if "검색" in text or "search" in lowered or "find" in lowered:
        return False
    if "http://" in lowered or "https://" in lowered:
        return False
    if is_generic_action_input(text):
        return False
    return True
