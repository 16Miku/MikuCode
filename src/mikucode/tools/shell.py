import subprocess
from pathlib import Path
from typing import Any

from mikucode.permissions.risk import classify_command
from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry


def register_shell_tool(registry: ToolRegistry, project_root: Path) -> None:
    root = project_root.resolve()

    def run_shell(arguments: dict[str, Any]) -> ToolResult:
        command = str(arguments["command"])
        timeout_seconds = int(arguments.get("timeout_seconds", 30))
        risk = classify_command(command)
        if risk.decision == "deny":
            return ToolResult(
                ok=False,
                tool="run_shell",
                summary=f"Command denied: {', '.join(risk.reasons)}",
                metadata={"risk_level": risk.level, "command": command},
            )
        if risk.decision == "ask":
            return ToolResult(
                ok=False,
                tool="run_shell",
                summary="Command requires user approval in B-version non-interactive tool path",
                metadata={"risk_level": risk.level, "command": command},
            )
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            partial = ((exc.stdout or "") + (exc.stderr or ""))[:20_000]
            return ToolResult(
                ok=False,
                tool="run_shell",
                summary=f"Command timed out after {timeout_seconds}s",
                content=partial if isinstance(partial, str) else "",
                metadata={
                    "command": command,
                    "exit_code": None,
                    "risk_level": risk.level,
                    "timeout": True,
                },
            )
        content = (completed.stdout + completed.stderr)[:20_000]
        return ToolResult(
            ok=completed.returncode == 0,
            tool="run_shell",
            summary=f"Command exited with {completed.returncode}",
            content=content,
            metadata={
                "command": command,
                "exit_code": completed.returncode,
                "risk_level": risk.level,
            },
        )

    registry.register(
        ToolDefinition(
            name="run_shell",
            description="Run a low-risk shell command inside the project root.",
            risk_level="medium",
            timeout=30,
            output_limit=20_000,
        ),
        run_shell,
    )
