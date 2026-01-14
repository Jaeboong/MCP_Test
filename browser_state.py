import os
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserState:
    def __init__(self) -> None:
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = False
        self.user_data_dir = Path("C:/ssafy/MCP/user_data")
        self.use_cdp = True
        self.cdp_url = os.environ.get("PLAYWRIGHT_CDP_URL", "http://127.0.0.1:9222")
        self.locale = "ko-KR"
        self.timezone_id = "Asia/Seoul"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
        self._page_listener_attached = False


state = BrowserState()


async def ensure_page() -> Page:
    if state.page is not None:
        return state.page

    if state.playwright is None:
        state.playwright = await async_playwright().start()

    if state.browser is None and state.use_cdp:
        state.browser = await state.playwright.chromium.connect_over_cdp(state.cdp_url)

    if state.context is None:
        if state.use_cdp and state.browser is not None:
            if state.browser.contexts:
                state.context = state.browser.contexts[0]
            else:
                state.context = await state.browser.new_context()
        else:
            state.user_data_dir.mkdir(parents=True, exist_ok=True)
            state.context = await state.playwright.chromium.launch_persistent_context(
                user_data_dir=str(state.user_data_dir),
                headless=state.headless,
                args=["--disable-blink-features=AutomationControlled"],
                locale=state.locale,
                timezone_id=state.timezone_id,
                user_agent=state.user_agent,
                viewport={"width": 1365, "height": 768},
                device_scale_factor=1.0,
                is_mobile=False,
                has_touch=False,
            )
            await state.context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            await state.context.set_extra_http_headers(
                {
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                }
            )

    if state.context is not None and not state._page_listener_attached:
        def _on_new_page(page: Page) -> None:
            state.page = page

        state.context.on("page", _on_new_page)
        state._page_listener_attached = True

    state.page = await state.context.new_page()
    return state.page


async def switch_to_latest_page() -> Page:
    if state.context is None:
        return await ensure_page()
    pages = state.context.pages
    if not pages:
        return await ensure_page()
    state.page = pages[-1]
    return state.page


async def shutdown_browser() -> None:
    if state.page is not None:
        await state.page.close()
        state.page = None

    if state.context is not None:
        await state.context.close()
        state.context = None
    state._page_listener_attached = False

    if state.browser is not None:
        await state.browser.close()
        state.browser = None

    if state.playwright is not None:
        await state.playwright.stop()
        state.playwright = None
