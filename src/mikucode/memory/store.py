from datetime import UTC, datetime
from pathlib import Path

from mikucode.config import ensure_miku_dir


class MemoryStore:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.miku_dir = ensure_miku_dir(self.project_root)
        self.project_md = self.miku_dir / "project.md"

    def read_project_memory(self) -> str:
        if self.project_md.exists():
            return self.project_md.read_text(encoding="utf-8")
        return ""

    def add_project_memory(self, text: str, source: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        with self.project_md.open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n## Memory entry\n"
                f"- created_at: {timestamp}\n"
                f"- source: {source}\n"
                f"- content: {text}\n"
            )
