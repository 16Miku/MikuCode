from pathlib import Path

from mikucode.permissions.policy import PathPolicy
from mikucode.tools.filesystem import register_filesystem_tools
from mikucode.tools.registry import ToolRegistry
from mikucode.tools.search import register_search_tools


def test_path_policy_allows_project_file(tmp_path: Path):
    file_path = tmp_path / "src" / "main.py"
    file_path.parent.mkdir()
    file_path.write_text("print('hi')", encoding="utf-8")

    policy = PathPolicy(tmp_path)

    assert policy.ensure_inside_project("src/main.py") == file_path.resolve()


def test_path_policy_denies_escape(tmp_path: Path):
    policy = PathPolicy(tmp_path)

    try:
        policy.ensure_inside_project("../secret.txt")
    except PermissionError as exc:
        assert "outside project root" in str(exc)
    else:
        raise AssertionError("Expected path escape denial")


def test_path_policy_denies_secret_file(tmp_path: Path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-secret", encoding="utf-8")
    policy = PathPolicy(tmp_path)

    try:
        policy.ensure_inside_project(".env")
    except PermissionError as exc:
        assert "secret" in str(exc)
    else:
        raise AssertionError("Expected secret file denial")


def test_path_policy_denies_git_internals(tmp_path: Path):
    policy = PathPolicy(tmp_path)

    try:
        policy.ensure_inside_project(".git/config")
    except PermissionError as exc:
        assert ".git" in str(exc)
    else:
        raise AssertionError("Expected .git internals denial")


def test_read_file_tool_reads_text_file(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("line1\nline2\n", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)

    result = registry.execute("read_file", {"path": "src/main.py"})

    assert result.ok is True
    assert "line1" in result.content
    assert result.metadata["path"] == "src/main.py"


def test_read_file_rejects_binary(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "blob.bin").write_bytes(b"\x00\x01\x02binary")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)

    result = registry.execute("read_file", {"path": "src/blob.bin"})

    assert result.ok is False
    assert "binary" in result.summary.lower()


def test_read_file_truncates_over_limit(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "big.txt").write_text("a" * 20_001, encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)

    result = registry.execute("read_file", {"path": "src/big.txt"})

    assert result.ok is True
    assert len(result.content) <= 20_000
    assert result.metadata["truncated"] is True


def test_list_files_ignores_cache_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)

    result = registry.execute("list_files", {})

    assert "src/main.py" in result.content
    assert ".venv/ignored.py" not in result.content


def test_search_text_finds_matches(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "parser.py").write_text(
        "def parse_config():\n    return {}\n", encoding="utf-8"
    )
    registry = ToolRegistry()
    register_search_tools(registry, tmp_path)

    result = registry.execute("search_text", {"query": "parse_config"})

    assert result.ok is True
    assert "src/parser.py:1" in result.content


def test_search_text_respects_max_results(tmp_path: Path):
    (tmp_path / "src").mkdir()
    lines = "\n".join(f"match_line_{i}" for i in range(20))
    (tmp_path / "src" / "many.py").write_text(lines + "\n", encoding="utf-8")
    registry = ToolRegistry()
    register_search_tools(registry, tmp_path)

    result = registry.execute("search_text", {"query": "match_line_", "max_results": 5})

    assert result.ok is True
    assert len([line for line in result.content.splitlines() if line]) == 5


def test_registry_unknown_tool_returns_failure():
    registry = ToolRegistry()

    result = registry.execute("nope", {})

    assert result.ok is False
    assert result.tool == "nope"
    assert "Unknown tool" in result.summary


def test_search_text_accepts_pattern_alias(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "risk.py").write_text(
        "def classify_command(command: str):\n    pass\n", encoding="utf-8"
    )
    registry = ToolRegistry()
    register_search_tools(registry, tmp_path)

    result = registry.execute("search_text", {"pattern": "classify_command"})

    assert result.ok is True
    assert "src/risk.py:1" in result.content


def test_search_text_missing_query_returns_failure(tmp_path: Path):
    registry = ToolRegistry()
    register_search_tools(registry, tmp_path)

    result = registry.execute("search_text", {})

    assert result.ok is False
    assert "query" in result.summary.lower()
