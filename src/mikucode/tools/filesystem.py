from pathlib import Path
from typing import Any

from mikucode.permissions.policy import PathPolicy
from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry

_IGNORED_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}
_DEFAULT_OUTPUT_LIMIT = 20_000


def register_filesystem_tools(registry: ToolRegistry, project_root: Path) -> None:
    root = project_root.resolve()
    policy = PathPolicy(root)
    read_definition = ToolDefinition(
        name="read_file",
        description="Read a UTF-8 text file inside the project root.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        timeout=5,
        output_limit=_DEFAULT_OUTPUT_LIMIT,
    )
    list_definition = ToolDefinition(
        name="list_files",
        description="List project files excluding common generated directories.",
        input_schema={"type": "object", "properties": {}},
        timeout=5,
        output_limit=_DEFAULT_OUTPUT_LIMIT,
    )

    def read_file(arguments: dict[str, Any]) -> ToolResult:
        path = str(arguments.get("path", ""))
        try:
            resolved = policy.ensure_inside_project(path)
            raw = resolved.read_bytes()
            if b"\x00" in raw:
                return ToolResult(
                    ok=False,
                    tool="read_file",
                    summary=f"Refusing to read binary file: {path}",
                    metadata={"path": path},
                )
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                return ToolResult(
                    ok=False,
                    tool="read_file",
                    summary=f"Failed to decode as UTF-8 text (binary or invalid encoding): {exc}",
                    metadata={"path": path},
                )
        except Exception as exc:
            return ToolResult(
                ok=False,
                tool="read_file",
                summary=str(exc),
                metadata={"path": path},
            )

        limit = read_definition.output_limit
        truncated = len(content) > limit
        return ToolResult(
            ok=True,
            tool="read_file",
            summary=f"Read {path}",
            content=content[:limit],
            metadata={"path": path, "truncated": truncated},
        )

    def list_files(arguments: dict[str, Any]) -> ToolResult:
        del arguments
        files: list[str] = []
        for item in root.rglob("*"):
            try:
                rel = item.relative_to(root)
            except ValueError:
                continue
            if any(part in _IGNORED_DIRS for part in rel.parts):
                continue
            if item.is_file():
                files.append(rel.as_posix())
        files.sort()
        return ToolResult(
            ok=True,
            tool="list_files",
            summary=f"Listed {len(files)} files",
            content="\n".join(files),
        )

    registry.register(read_definition, read_file)
    registry.register(list_definition, list_files)
