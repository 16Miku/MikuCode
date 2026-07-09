import json
import shutil
from pathlib import Path

from mikucode.runtime.actions import ToolResult


class UndoManager:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def undo_last(self) -> ToolResult:
        manifest_path = self.project_root / ".miku" / "backups" / "last.json"
        if not manifest_path.exists():
            return ToolResult(ok=False, tool="undo", summary="No backup manifest found")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        patch_id = manifest["patch_id"]
        restored: list[str] = []
        for relative_path in manifest["files"]:
            backup = self.project_root / ".miku" / "backups" / patch_id / relative_path
            target = self.project_root / relative_path
            if not backup.exists():
                return ToolResult(
                    ok=False,
                    tool="undo",
                    summary=f"Missing backup: {backup}",
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(relative_path)
        return ToolResult(
            ok=True,
            tool="undo",
            summary=f"Restored {len(restored)} file(s)",
            metadata={"restored": restored},
        )
