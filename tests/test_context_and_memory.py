from pathlib import Path

from mikucode.config import ensure_miku_dir
from mikucode.context.builder import ContextBuilder
from mikucode.context.file_tree import build_file_tree
from mikucode.memory.store import MemoryStore
from mikucode.runtime.actions import ToolResult
from mikucode.runtime.state import AgentState


def test_build_file_tree_ignores_generated_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("", encoding="utf-8")

    tree = build_file_tree(tmp_path)

    assert "src/main.py" in tree
    assert ".venv/ignored.py" not in tree


def test_memory_store_reads_and_appends_project_memory(tmp_path: Path):
    ensure_miku_dir(tmp_path)
    store = MemoryStore(tmp_path)

    store.add_project_memory("Use uv run pytest for tests.", source="user")

    memory = store.read_project_memory()
    assert "Use uv run pytest" in memory
    assert "source: user" in memory


def test_context_builder_includes_task_memory_tree_and_recent_observation(tmp_path: Path):
    ensure_miku_dir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "parser.py").write_text("def parse(): pass", encoding="utf-8")
    state = AgentState.new("fix parser")
    state.record_observation(
        ToolResult(ok=False, tool="run_tests", summary="parser test failed")
    )

    messages = ContextBuilder(tmp_path).build(state)
    joined = "\n".join(message["content"] for message in messages)

    assert "fix parser" in joined
    assert "src/parser.py" in joined
    assert "parser test failed" in joined
