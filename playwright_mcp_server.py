import json
import random
import sys

from mcp.server.fastmcp import FastMCP
from playwright.async_api import Page

from browser_state import ensure_page, shutdown_browser, state, switch_to_latest_page
from generic_actions import action_terms_for_input

mcp = FastMCP("playwright-mcp")


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
async def click_in_frames(selector: str) -> str:
    """
    Click the first element matching selector across frames.
    """
    page = await ensure_page()
    for frame in page.frames:
        try:
            locator = frame.locator(selector)
        except Exception:
            continue
        try:
            if await locator.count() > 0:
                await locator.first.click()
                return f"clicked {selector}"
        except Exception:
            continue
    return f"not_found_selector {selector}"


@mcp.tool()
async def click_text(text: str) -> str:
    """
    Click the first element that matches the given text, across frames.
    """
    page = await ensure_page()
    terms = action_terms_for_input(text) or [text]

    async def _click_first(locator) -> bool:
        try:
            if await locator.count() > 0:
                await locator.first.click()
                return True
        except Exception:
            return False
        return False

    for frame in page.frames:
        for term in terms:
            if await _click_first(frame.get_by_role("button", name=term)):
                return f"clicked_text {term}"
            if await _click_first(frame.get_by_text(term)):
                return f"clicked_text {term}"
            selectors = [
                f"[aria-label*='{term}']",
                f"[title*='{term}']",
                f"input[value*='{term}']",
            ]
            for selector in selectors:
                try:
                    locator = frame.locator(selector)
                except Exception:
                    continue
                if await _click_first(locator):
                    return f"clicked_text {term}"
    return f"not_found_text {text}"


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
      (maxItems, includePadKeys) => {
        const selectors = [
          "button",
          "a[role='button']",
          "input[type='button']",
          "input[type='submit']",
        ];
        if (includePadKeys) {
          selectors.push("a.pad-key");
        }
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
            dataKey: el.getAttribute("data-key") || "",
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
        include_pad_keys = "coupang.com" in frame.url
        try:
            items = await frame.evaluate(selector_script, remaining, include_pad_keys)
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
    await shutdown_browser()
    return "browser_closed"


@mcp.tool()
async def switch_latest_page() -> str:
    """
    Switch to the most recently opened page in the current context.
    """
    page = await switch_to_latest_page()
    return f"switched {page.url}"


def main() -> None:
    print("playwright_mcp_server starting", file=sys.stderr, flush=True)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
