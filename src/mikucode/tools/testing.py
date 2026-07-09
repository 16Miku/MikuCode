from pathlib import Path
from typing import Any

from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry
from mikucode.verification.detector import detect_test_command
from mikucode.verification.runner import VerificationRunner


def register_testing_tools(registry: ToolRegistry, project_root: Path) -> None:
    root = project_root.resolve()

    def detect_tests(arguments: dict[str, Any]) -> ToolResult:
        del arguments
        command = detect_test_command(root)
        return ToolResult(
            ok=True,
            tool="detect_tests",
            summary=f"Detected test command: {command}",
            metadata={"command": command},
        )

    def run_tests(arguments: dict[str, Any]) -> ToolResult:
        command = arguments.get("command")
        return VerificationRunner(root, command=command).run()

    registry.register(
        ToolDefinition(name="detect_tests", description="Detect the project test command."),
        detect_tests,
    )
    registry.register(
        ToolDefinition(
            name="run_tests",
            description="Run the project test command through the shell policy.",
        ),
        run_tests,
    )
