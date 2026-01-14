import random
import sys
from pathlib import Path
from typing import Optional
import os
import json

from mcp.server.fastmcp import FastMCP
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

mcp = FastMCP("playwright-mcp")


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


@mcp.tool()
async def start_browser(headless: bool = False) -> str:
    """
    Start a Chromium browser instance if not already running.
    """
    state.headless = headless
    await ensure_page()
    return f"browser_started headless={state.headless}"


@mcp.tool()
async def open_url(url: str) -> str:
    """
    Navigate to a URL.
    """
    page = await ensure_page()
    await page.goto(url, wait_until="domcontentloaded")
    title = await page.title()
    return f"opened {url} title={title}"


@mcp.tool()
async def click(selector: str) -> str:
    """
    Click an element by selector.
    """
    page = await ensure_page()
    await page.click(selector)
    return f"clicked {selector}"


@mcp.tool()
async def fill(selector: str, text: str) -> str:
    """
    Fill an input by selector.
    """
    page = await ensure_page()
    await page.fill(selector, text)
    return f"filled {selector}"


@mcp.tool()
async def press(selector: str, key: str) -> str:
    """
    Press a key on a focused element.
    """
    page = await ensure_page()
    await page.press(selector, key)
    return f"pressed {key} on {selector}"


@mcp.tool()
async def wait(ms: int) -> str:
    """
    Wait for a number of milliseconds.
    """
    page = await ensure_page()
    await page.wait_for_timeout(ms)
    return f"waited {ms}ms"


@mcp.tool()
async def scroll(delta_y: int) -> str:
    """
    Scroll the page by delta_y pixels.
    """
    page = await ensure_page()
    await page.mouse.wheel(0, delta_y)
    return f"scrolled {delta_y}"


@mcp.tool()
async def humanize(steps: int = 3, min_wait_ms: int = 200, max_wait_ms: int = 800, max_scroll: int = 800) -> str:
    """
    Perform small human-like actions: move mouse, scroll, and wait.
    """
    page = await ensure_page()
    size = page.viewport_size or {"width": 1280, "height": 720}
    width = size.get("width", 1280)
    height = size.get("height", 720)

    for _ in range(max(1, steps)):
        x = random.randint(10, max(10, width - 10))
        y = random.randint(10, max(10, height - 10))
        await page.mouse.move(x, y, steps=random.randint(5, 20))
        await page.wait_for_timeout(random.randint(min_wait_ms, max_wait_ms))
        if max_scroll > 0 and random.random() < 0.7:
            delta = random.randint(-max_scroll, max_scroll)
            if delta != 0:
                await page.mouse.wheel(0, delta)
                await page.wait_for_timeout(random.randint(min_wait_ms, max_wait_ms))

    return "humanized"


@mcp.tool()
async def get_text(max_chars: int = 2000) -> str:
    """
    Return visible text from the page (truncated).
    """
    page = await ensure_page()
    text = await page.evaluate("() => document.body?.innerText || ''")
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


@mcp.tool()
async def get_visible_buttons(max_items: int = 200) -> str:
    """
    Return visible button-like elements with class and label text, across frames.
    """
    page = await ensure_page()
    selector_script = """
      (maxItems) => {
        const selectors = [
          "button",
          "a[role='button']",
          "input[type='button']",
          "input[type='submit']",
        ];
        const nodes = Array.from(document.querySelectorAll(selectors.join(",")));
        const visible = [];
        for (const el of nodes) {
          if (visible.length >= maxItems) break;
          const rect = el.getBoundingClientRect();
          if (!rect || rect.width === 0 || rect.height === 0) continue;
          const style = window.getComputedStyle(el);
          if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") continue;
          const text = (el.innerText || el.value || el.getAttribute("aria-label") || "").trim();
          visible.push({
            class: (el.className || "").toString(),
            text,
          });
        }
        return visible;
      }
    """
    results = []
    remaining = max_items
    for frame in page.frames:
        if remaining <= 0:
            break
        try:
            items = await frame.evaluate(selector_script, remaining)
        except Exception:
            continue
        if not items:
            continue
        for item in items:
            if remaining <= 0:
                break
            item["frameUrl"] = frame.url
            results.append(item)
            remaining -= 1

    return json.dumps(results, ensure_ascii=True)


@mcp.tool()
async def screenshot(path: str, full_page: bool = True) -> str:
    """
    Take a screenshot to a local path.
    """
    page = await ensure_page()
    await page.screenshot(path=path, full_page=full_page)
    return f"screenshot {path}"


@mcp.tool()
async def close_browser() -> str:
    """
    Close browser/context and stop Playwright.
    """
    if state.page is not None:
        await state.page.close()
        state.page = None

    if state.context is not None:
        await state.context.close()
        state.context = None
    state._page_listener_attached = False


@mcp.tool()
async def switch_latest_page() -> str:
    """
    Switch to the most recently opened page in the current context.
    """
    page = await switch_to_latest_page()
    return f"switched {page.url}"

    if state.browser is not None:
        await state.browser.close()
        state.browser = None

    if state.playwright is not None:
        await state.playwright.stop()
        state.playwright = None

    return "browser_closed"


def main() -> None:
    print("playwright_mcp_server starting", file=sys.stderr, flush=True)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
