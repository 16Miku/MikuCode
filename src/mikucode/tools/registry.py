from typing import Any

from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition, ToolExecutor


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._executors: dict[str, ToolExecutor] = {}

    def register(self, definition: ToolDefinition, executor: ToolExecutor) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._definitions[definition.name] = definition
        self._executors[definition.name] = executor

    def definition(self, name: str) -> ToolDefinition:
        return self._definitions[name]

    def definitions(self) -> list[ToolDefinition]:
        return list(self._definitions.values())

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if name not in self._executors:
            return ToolResult(ok=False, tool=name, summary=f"Unknown tool: {name}")
        return self._executors[name](arguments)
