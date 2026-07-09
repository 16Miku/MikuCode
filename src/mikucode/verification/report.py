from typing import Any

from mikucode.runtime.actions import ToolResult


def summarize_verification(result: ToolResult) -> dict[str, Any]:
    return {
        "command": result.metadata.get("command", "unknown"),
        "exit_code": result.metadata.get("exit_code"),
        "summary": result.summary,
        "passed": result.ok,
    }
