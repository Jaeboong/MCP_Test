import asyncio
import datetime
import os
import sys
from typing import Any, Dict, List, Tuple

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from cli_logging import log_llm_calls
from cli_parser import parse_command, print_help
from llm_translate import translate_with_llm
from rule_based import rule_based_commands
from shopping_sites import should_click_search_result


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


async def main() -> None:
    load_dotenv()
    print("Starting MCP server...", flush=True)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-u", "playwright_mcp_server.py"],
        env={"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    err_path = "mcp_server.err.log"
    last_open_url = ""
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
                    from_llm = False
                    if tool_name:
                        tool_calls.append((tool_name, arguments))
                    else:
                        tool_calls = rule_based_commands(line)
                        if not tool_calls:
                            if should_click_search_result(line, last_open_url):
                                tool_calls = [("click_text", {"text": line})]
                            if not tool_calls:
                                tool_calls = translate_with_llm(line)
                                from_llm = bool(tool_calls)
                        if not tool_calls:
                            print("Could not map input to a tool. Try a command or set OPENAI_API_KEY.")
                            continue

                    if from_llm:
                        log_llm_calls(line, tool_calls)

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
                        if tool_name == "open_url":
                            last_open_url = arguments.get("url", last_open_url)


if __name__ == "__main__":
    asyncio.run(main())
