from pathlib import Path


def detect_test_command(project_root: Path) -> str:
    if (project_root / "pyproject.toml").exists() and (project_root / "uv.lock").exists():
        return "uv run pytest"
    if (project_root / "pyproject.toml").exists():
        return "uv run pytest"
    if (project_root / "pytest.ini").exists() or (project_root / "tests").exists():
        return "python -m pytest"
    return "uv run pytest"
