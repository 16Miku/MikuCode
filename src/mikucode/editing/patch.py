from pathlib import Path
from typing import Any

from mikucode.config import ensure_miku_dir
from mikucode.editing.backup import create_backup
from mikucode.editing.diff import unified_diff
from mikucode.permissions.policy import PathPolicy
from mikucode.runtime.actions import ToolResult


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class PatchEngine:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        ensure_miku_dir(self.project_root)
        self.path_policy = PathPolicy(self.project_root)

    def apply_patches(self, patches: list[dict[str, Any]]) -> ToolResult:
        if not patches:
            return ToolResult(ok=False, tool="apply_patch", summary="No patches provided")
        diffs: list[str] = []
        changed: list[str] = []
        for patch in patches:
            kind = patch.get("kind")
            if kind == "search_replace":
                result = self._apply_search_replace(patch)
            elif kind == "create_file":
                result = self._apply_create_file(patch)
            else:
                return ToolResult(
                    ok=False,
                    tool="apply_patch",
                    summary=f"Unsupported patch kind: {kind}",
                )
            if not result.ok:
                return result
            diffs.append(result.content)
            changed.append(str(result.metadata["path"]))
        return ToolResult(
            ok=True,
            tool="apply_patch",
            summary=f"Applied {len(changed)} patch(es)",
            content="\n".join(diffs),
            metadata={"changed_files": changed},
        )

    def _apply_search_replace(self, patch: dict[str, Any]) -> ToolResult:
        path = str(patch["path"])
        # Normalize newlines so Windows CRLF files match model-provided LF snippets.
        old_text = _normalize_newlines(str(patch["old_text"]))
        new_text = _normalize_newlines(str(patch["new_text"]))
        try:
            resolved = self.path_policy.ensure_inside_project(path)
            before = _normalize_newlines(resolved.read_text(encoding="utf-8"))
        except Exception as exc:
            return ToolResult(
                ok=False,
                tool="apply_patch",
                summary=str(exc),
                metadata={"path": path},
            )
        count = before.count(old_text)
        if count != 1:
            preview = before if len(before) <= 240 else before[:240] + "…"
            return ToolResult(
                ok=False,
                tool="apply_patch",
                summary=(
                    f"old_text must match exactly once; got {count}. "
                    f"old_text={old_text!r} file_preview={preview!r}"
                ),
                metadata={"path": path, "match_count": count},
            )
        after = before.replace(old_text, new_text, 1)
        create_backup(self.project_root, path)
        # Write with explicit newlines for stable cross-platform content.
        resolved.write_text(after, encoding="utf-8", newline="\n")
        diff = unified_diff(path, before, after)
        patches_dir = self.project_root / ".miku" / "patches"
        patches_dir.mkdir(parents=True, exist_ok=True)
        (patches_dir / "last.diff").write_text(diff, encoding="utf-8")
        return ToolResult(
            ok=True,
            tool="apply_patch",
            summary=f"Patched {path}",
            content=diff,
            metadata={"path": path},
        )

    def _apply_create_file(self, patch: dict[str, Any]) -> ToolResult:
        path = str(patch["path"])
        content = str(patch["content"])
        try:
            resolved = self.path_policy.ensure_inside_project(path)
        except Exception as exc:
            return ToolResult(
                ok=False,
                tool="apply_patch",
                summary=str(exc),
                metadata={"path": path},
            )
        if resolved.exists():
            return ToolResult(
                ok=False,
                tool="apply_patch",
                summary=f"File already exists: {path}",
                metadata={"path": path},
            )
        resolved.parent.mkdir(parents=True, exist_ok=True)
        before = ""
        resolved.write_text(content, encoding="utf-8")
        diff = unified_diff(path, before, content)
        return ToolResult(
            ok=True,
            tool="apply_patch",
            summary=f"Created {path}",
            content=diff,
            metadata={"path": path},
        )
