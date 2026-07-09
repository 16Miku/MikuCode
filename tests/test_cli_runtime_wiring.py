from pathlib import Path

from typer.testing import CliRunner

from mikucode.cli.main import app


def test_one_shot_mock_runtime_reads_file(tmp_path: Path, monkeypatch):
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setenv(
        "MIKU_MOCK_RESPONSES",
        '[{"type":"tool_call","tool":"read_file","arguments":{"path":"hello.txt"},"reason":"Read"},{"type":"final_answer","summary":"done"}]',
    )
    runner = CliRunner()

    result = runner.invoke(app, ["--project-root", str(tmp_path), "read hello"])

    assert result.exit_code == 0, result.stdout + result.stderr
    assert "done" in result.stdout
    assert list((tmp_path / ".miku" / "sessions").glob("*.jsonl"))


def test_undo_command_reports_no_backup(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(app, ["undo", "--project-root", str(tmp_path)])

    assert result.exit_code == 0, result.stdout + result.stderr
    assert "No backup" in result.stdout
