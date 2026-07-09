from pathlib import Path

from mikucode.editing.patch import PatchEngine
from mikucode.editing.undo import UndoManager


def test_search_replace_patch_applies_and_creates_diff(tmp_path: Path):
    target = tmp_path / "src" / "parser.py"
    target.parent.mkdir()
    target.write_text("def parse(text):\n    return parse_raw(text)\n", encoding="utf-8")
    engine = PatchEngine(tmp_path)

    result = engine.apply_patches(
        [
            {
                "kind": "search_replace",
                "path": "src/parser.py",
                "old_text": "return parse_raw(text)",
                "new_text": "return parse_raw(text.strip())",
            }
        ]
    )

    assert result.ok is True
    assert "-    return parse_raw(text)" in result.content
    assert "+    return parse_raw(text.strip())" in result.content
    assert "text.strip()" in target.read_text(encoding="utf-8")
    assert list((tmp_path / ".miku" / "backups").rglob("parser.py"))


def test_search_replace_requires_unique_old_text(tmp_path: Path):
    target = tmp_path / "main.py"
    target.write_text("x = 1\nx = 1\n", encoding="utf-8")
    engine = PatchEngine(tmp_path)

    result = engine.apply_patches(
        [{"kind": "search_replace", "path": "main.py", "old_text": "x = 1", "new_text": "x = 2"}]
    )

    assert result.ok is False
    assert "exactly once" in result.summary
    assert target.read_text(encoding="utf-8") == "x = 1\nx = 1\n"


def test_create_file_fails_if_file_exists(tmp_path: Path):
    (tmp_path / "notes.md").write_text("existing", encoding="utf-8")
    engine = PatchEngine(tmp_path)

    result = engine.apply_patches(
        [{"kind": "create_file", "path": "notes.md", "content": "new"}]
    )

    assert result.ok is False
    assert "already exists" in result.summary


def test_undo_restores_last_patch(tmp_path: Path):
    target = tmp_path / "main.py"
    target.write_text("value = 1\n", encoding="utf-8")
    engine = PatchEngine(tmp_path)
    engine.apply_patches(
        [
            {
                "kind": "search_replace",
                "path": "main.py",
                "old_text": "value = 1",
                "new_text": "value = 2",
            }
        ]
    )

    result = UndoManager(tmp_path).undo_last()

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "value = 1\n"
