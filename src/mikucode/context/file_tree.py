from pathlib import Path

_IGNORED_DIRS = {
    ".git",
    ".miku",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
}


def build_file_tree(project_root: Path, max_files: int = 200) -> str:
    root = project_root.resolve()
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
        if len(files) >= max_files:
            break
    files.sort()
    return "\n".join(files)
