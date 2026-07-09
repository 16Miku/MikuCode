from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MikuConfig:
    project_root: Path
    miku_dir: Path
    permission_mode: str = "auto-safe"
    default_test_command: str = "uv run pytest"


def ensure_miku_dir(project_root: Path) -> Path:
    root = project_root.resolve()
    miku_dir = root / ".miku"
    (miku_dir / "sessions").mkdir(parents=True, exist_ok=True)
    (miku_dir / "patches").mkdir(parents=True, exist_ok=True)
    (miku_dir / "backups").mkdir(parents=True, exist_ok=True)

    project_md = miku_dir / "project.md"
    if not project_md.exists():
        project_md.write_text(
            "# MikuCode Project Memory\n\n"
            "## Commands\n"
            "- Test: uv run pytest\n\n"
            "## Conventions\n"
            "- Do not edit generated files.\n",
            encoding="utf-8",
        )

    config_toml = miku_dir / "config.toml"
    if not config_toml.exists():
        config_toml.write_text(
            'permission_mode = "auto-safe"\n\n'
            "[verification]\n"
            'test_command = "uv run pytest"\n',
            encoding="utf-8",
        )

    return miku_dir


def load_config(project_root: Path) -> MikuConfig:
    root = project_root.resolve()
    miku_dir = ensure_miku_dir(root)
    return MikuConfig(project_root=root, miku_dir=miku_dir)
