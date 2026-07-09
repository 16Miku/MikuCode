from pathlib import Path

from typer.testing import CliRunner

from mikucode.cli.main import app


def test_init_creates_miku_project_files(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / ".miku").is_dir()
    assert (tmp_path / ".miku" / "project.md").is_file()
    assert (tmp_path / ".miku" / "config.toml").is_file()
    assert (tmp_path / ".miku" / "sessions").is_dir()
    assert (tmp_path / ".miku" / "patches").is_dir()
    assert (tmp_path / ".miku" / "backups").is_dir()
    assert "Initialized MikuCode" in result.stdout


def test_init_is_idempotent_and_does_not_overwrite_existing_files(tmp_path: Path):
    runner = CliRunner()
    miku_dir = tmp_path / ".miku"
    miku_dir.mkdir()
    project_md = miku_dir / "project.md"
    config_toml = miku_dir / "config.toml"
    project_md.write_text("custom project memory", encoding="utf-8")
    config_toml.write_text("permission_mode = \"ask\"\n", encoding="utf-8")

    result = runner.invoke(app, ["init", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert project_md.read_text(encoding="utf-8") == "custom project memory"
    assert config_toml.read_text(encoding="utf-8") == "permission_mode = \"ask\"\n"
    assert (miku_dir / "sessions").is_dir()
    assert (miku_dir / "patches").is_dir()
    assert (miku_dir / "backups").is_dir()


def test_chat_command_starts_and_exits(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--project-root", str(tmp_path)], input="/exit\n")

    assert result.exit_code == 0
    assert "MikuCode" in result.stdout


def test_one_shot_task_initializes_project_without_provider_config(tmp_path: Path):
    """Without MIKU_MOCK_RESPONSES or API key, runtime fails after .miku init."""
    runner = CliRunner()

    result = runner.invoke(app, ["--project-root", str(tmp_path), "explain this project"])

    assert (tmp_path / ".miku" / "sessions").is_dir()
    assert result.exit_code == 1
    assert "API key" in result.stdout or "Runtime error" in result.stdout
