from pathlib import Path
from typing import Any

from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry

_IGNORED_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}


def _extract_search_query(arguments: dict[str, Any]) -> str | None:
    """Accept common argument aliases models invent for search tools."""
    for key in ("query", "pattern", "text", "q", "search", "keyword", "needle"):
        value = arguments.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def register_search_tools(registry: ToolRegistry, project_root: Path) -> None:
    root = project_root.resolve()

    def search_text(arguments: dict[str, Any]) -> ToolResult:
        query = _extract_search_query(arguments)
        if not query:
            return ToolResult(
                ok=False,
                tool="search_text",
                summary=(
                    "Missing required argument 'query' "
                    "(also accepted: pattern, text, q, search, keyword)."
                ),
                metadata={"arguments": arguments},
            )
        max_results = int(arguments.get("max_results", 50))
        matches: list[str] = []
        for item in root.rglob("*"):
            try:
                rel = item.relative_to(root)
            except ValueError:
                continue
            if any(part in _IGNORED_DIRS for part in rel.parts):
                continue
            if not item.is_file():
                continue
            try:
                lines = item.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for index, line in enumerate(lines, start=1):
                if query in line:
                    matches.append(f"{rel.as_posix()}:{index}: {line.strip()}")
                    if len(matches) >= max_results:
                        return ToolResult(
                            ok=True,
                            tool="search_text",
                            summary=f"Found {len(matches)} matches",
                            content="\n".join(matches),
                        )
        return ToolResult(
            ok=True,
            tool="search_text",
            summary=f"Found {len(matches)} matches",
            content="\n".join(matches),
        )

    registry.register(
        ToolDefinition(
            name="search_text",
            description="Search text in UTF-8 files inside the project root.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        ),
        search_text,
    )
