import asyncio
import datetime
import json
import os
import re
import shlex
import sys
from typing import Any, Dict, List, Optional, Tuple

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import httpx
from sites.coupang import coupang_logout_commands, coupang_selectors, coupang_urls
from sites.naver import naver_shopping_search_url


KNOWN_COMMANDS = {
    "open",
    "click",
    "fill",
    "press",
    "wait",
    "scroll",
    "humanize",
    "text",
    "buttons",
    "shot",
    "start",
    "close",
    "switch",
}


def parse_command(line: str) -> Tuple[Optional[str], Dict[str, Any]]:
    parts = shlex.split(line)
    if not parts:
        return None, {}

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd not in KNOWN_COMMANDS:
        return None, {}

    if cmd == "open" and args:
        return "open_url", {"url": args[0]}
    if cmd == "click" and args:
        return "click", {"selector": args[0]}
    if cmd == "fill" and len(args) >= 2:
        return "fill", {"selector": args[0], "text": " ".join(args[1:])}
    if cmd == "press" and len(args) >= 2:
        return "press", {"selector": args[0], "key": args[1]}
    if cmd == "wait" and args:
        return "wait", {"ms": int(args[0])}
    if cmd == "scroll" and args:
        return "scroll", {"delta_y": int(args[0])}
    if cmd == "humanize":
        steps = int(args[0]) if args else 3
        return "humanize", {"steps": steps}
    if cmd == "text":
        max_chars = int(args[0]) if args else 2000
        return "get_text", {"max_chars": max_chars}
    if cmd == "buttons":
        max_items = int(args[0]) if args else 200
        return "get_visible_buttons", {"max_items": max_items}
    if cmd == "shot" and args:
        return "screenshot", {"path": args[0], "full_page": True}
    if cmd == "start":
        headless = bool(args and args[0].lower() == "headless")
        return "start_browser", {"headless": headless}
    if cmd == "close":
        return "close_browser", {}
    if cmd == "switch":
        return "switch_latest_page", {}

    return None, {}


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _extract_response_text(data: Dict[str, Any]) -> str:
    if "output_text" in data and isinstance(data["output_text"], str):
        return data["output_text"]
    output = data.get("output", [])
    for item in output:
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content.get("text", "")
    return ""


def _json_from_text(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _format_tools_for_prompt() -> str:
    return "\n".join(
        [
            "- start_browser(headless: bool)",
            "- open_url(url: str)",
            "- click(selector: str)",
            "- fill(selector: str, text: str)",
            "- press(selector: str, key: str)",
            "- wait(ms: int)",
            "- scroll(delta_y: int)",
            "- humanize(steps: int, min_wait_ms: int, max_wait_ms: int, max_scroll: int)",
            "- get_text(max_chars: int)",
            "- get_visible_buttons(max_items: int)",
            "- screenshot(path: str, full_page: bool)",
            "- switch_latest_page()",
            "- close_browser()",
        ]
    )


def translate_with_llm(user_text: str, model: str = "gpt-5-mini") -> List[Tuple[str, Dict[str, Any]]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []
    model = os.environ.get("OPENAI_MODEL", model)
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    system_prompt = (
        "You convert natural language into Playwright MCP tool calls. "
        "Return ONLY valid JSON. Allowed tools:\n"
        f"{_format_tools_for_prompt()}\n"
        "If multiple steps are needed, return:\n"
        '{"commands":[{"tool":"open_url","arguments":{"url":"https://example.com"}}]}\n'
        "If one step, return:\n"
        '{"tool":"open_url","arguments":{"url":"https://example.com"}}'
    )

    payload = {
        "model": model,
        "instructions": system_prompt,
        "input": user_text,
        "reasoning": {"effort": "minimal"},
        "text": {"verbosity": "low"},
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(f"{base_url}/responses", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        print(f"llm error: {exc} body={body}")
        return []
    except httpx.HTTPError as exc:
        print(f"llm error: {exc}")
        return []

    text = _extract_response_text(data)
    parsed = _json_from_text(text)
    if not parsed:
        return []

    commands = parsed.get("commands")
    if isinstance(commands, list):
        results = []
        for item in commands:
            tool = item.get("tool")
            args = item.get("arguments", {})
            if tool and isinstance(args, dict):
                results.append((tool, args))
        return results

    tool = parsed.get("tool")
    args = parsed.get("arguments", {})
    if tool and isinstance(args, dict):
        return [(tool, args)]

    return []


def rule_based_commands(user_text: str) -> List[Tuple[str, Dict[str, Any]]]:
    text = user_text.strip()
    if not text:
        return []

    coupang = coupang_urls()
    cs = coupang_selectors()

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

    if text == "로그아웃":
        return coupang_logout_commands()

    if "로그인" in text and "버튼" in text:
        return [
            ("start_browser", {"headless": False}),
            ("click", {"selector": cs["login_button"]}),
        ]

    if "쿠팡" in text and "검색" in text:
        m = re.search(r"쿠팡(?:에|에서)?\\s*(.+?)\\s*검색", text)
        query = m.group(1) if m else text.replace("쿠팡", "").replace("검색", "").strip()
        if query:
            return [
                ("start_browser", {"headless": False}),
                ("open_url", {"url": coupang["home"]}),
                ("wait", {"ms": 800}),
                ("click", {"selector": cs["search_input"]}),
                ("fill", {"selector": cs["search_input"], "text": query}),
                ("press", {"selector": cs["search_input"], "key": "Enter"}),
            ]

    # Simple Korean search patterns: "쿠팡에 생수 검색해줘", "생수 검색해"
    if "쿠팡" in text and "검색" in text:
        m = re.search(r"쿠팡(?:에|에서)?\\s*(.+?)\\s*검색", text)
        query = m.group(1) if m else text.replace("쿠팡", "").replace("검색", "").strip()
        if query:
            return [
                ("start_browser", {"headless": False}),
                ("open_url", {"url": "https://www.coupang.com"}),
                ("wait", {"ms": 1500}),
                ("click", {"selector": "input[name=\"q\"]"}),
                ("fill", {"selector": "input[name=\"q\"]", "text": query}),
                ("press", {"selector": "input[name=\"q\"]", "key": "Enter"}),
            ]

    if ("네이버" in text and "쇼핑" in text and "검색" in text) or ("네이버" in text and "검색" in text):
        m = re.search(r"네이버(?:\\s*쇼핑)?(?:에|에서)?\\s*(.+?)\\s*검색", text)
        query = m.group(1) if m else text.replace("네이버", "").replace("쇼핑", "").replace("검색", "").strip()
        if query:
            return [
                ("start_browser", {"headless": False}),
                ("open_url", {"url": naver_shopping_search_url(query)}),
                ("wait", {"ms": 800}),
            ]

    if "검색" in text:
        m = re.search(r"(.+?)\\s*검색", text)
        query = m.group(1).strip() if m else ""
        if query:
            return [
                ("start_browser", {"headless": False}),
                ("open_url", {"url": "https://www.google.com"}),
                ("wait", {"ms": 800}),
                ("click", {"selector": "input[name=\"q\"]"}),
                ("fill", {"selector": "input[name=\"q\"]", "text": query}),
                ("press", {"selector": "input[name=\"q\"]", "key": "Enter"}),
            ]

    return []


def print_help() -> None:
    print("Commands:")
    print("  start [headless]")
    print("  open <url>")
    print("  click <selector>")
    print("  fill <selector> <text>")
    print("  press <selector> <key>")
    print("  wait <ms>")
    print("  scroll <pixels>")
    print("  humanize [steps]")
    print("  text [max_chars]")
    print("  buttons [max_items]")
    print("  shot <path>")
    print("  switch")
    print("  close")
    print("  exit | quit")


async def main() -> None:
    load_dotenv()
    print("Starting MCP server...", flush=True)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-u", "playwright_mcp_server.py"],
        env={"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    err_path = "mcp_server.err.log"
    with open(err_path, "w", encoding="utf-8") as errlog:
        async with stdio_client(server, errlog=errlog) as (read, write):
            async with ClientSession(
                read,
                write,
                read_timeout_seconds=datetime.timedelta(seconds=60),
            ) as session:
                try:
                    await session.initialize()
                except Exception as exc:
                    print(f"init failed: {exc}")
                    print(f"see {err_path}")
                    return

                while True:
                    try:
                        line = input("> ").strip()
                    except EOFError:
                        break
                    if not line:
                        line = "text"
                    if line.lower() in {"exit", "quit"}:
                        break
                    if line.lower() == "help":
                        print_help()
                        continue

                    tool_name, arguments = parse_command(line)
                    tool_calls: List[Tuple[str, Dict[str, Any]]] = []
                    if tool_name:
                        tool_calls.append((tool_name, arguments))
                    else:
                        tool_calls = rule_based_commands(line)
                        if not tool_calls:
                            tool_calls = translate_with_llm(line)
                        if not tool_calls:
                            print("Could not map input to a tool. Try a command or set OPENAI_API_KEY.")
                            continue

                    for tool_name, arguments in tool_calls:
                        try:
                            result = await session.call_tool(tool_name, arguments)
                        except Exception as exc:
                            print(f"error: {exc}")
                            break

                        if result.isError:
                            print("tool_error")
                            for item in result.content:
                                if hasattr(item, "text"):
                                    print(item.text)
                            break

                        for item in result.content:
                            if hasattr(item, "text"):
                                print(item.text)


if __name__ == "__main__":
    asyncio.run(main())
