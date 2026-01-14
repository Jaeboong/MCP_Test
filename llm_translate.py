import json
import os
from typing import Any, Dict, List, Tuple

import httpx


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
            "- click_in_frames(selector: str)",
            "- click_text(text: str)",
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
