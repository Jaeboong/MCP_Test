import datetime
import json
from typing import Any, Dict, List, Tuple


def log_llm_calls(
    user_text: str, tool_calls: List[Tuple[str, Dict[str, Any]]], path: str = "llm_tool_calls.log"
) -> None:
    if not tool_calls:
        return
    record = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "input": user_text,
        "tool_calls": [{"tool": name, "arguments": args} for name, args in tool_calls],
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
