from pathlib import Path

from mikucode.runtime.actions import ToolResult
from mikucode.tools.registry import ToolRegistry
from mikucode.tools.shell import register_shell_tool
from mikucode.verification.detector import detect_test_command


class VerificationRunner:
    def __init__(self, project_root: Path, command: str | None = None) -> None:
        self.project_root = project_root.resolve()
        self.command = command or detect_test_command(self.project_root)

    def run(self) -> ToolResult:
        registry = ToolRegistry()
        register_shell_tool(registry, self.project_root)
        result = registry.execute(
            "run_shell",
            {"command": self.command, "timeout_seconds": 120},
        )
        result.tool = "run_tests"
        return result
