import os
from pathlib import Path

from mikucode.config import load_env_files


def test_load_env_files_reads_dotenv_without_overriding_existing(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MIKU_TEST_FROM_FILE=from-file\nMIKU_TEST_OVERRIDE=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MIKU_TEST_FROM_FILE", raising=False)
    monkeypatch.setenv("MIKU_TEST_OVERRIDE", "from-shell")

    loaded = load_env_files(tmp_path)

    assert env_file.resolve() in loaded
    assert os.environ.get("MIKU_TEST_FROM_FILE") == "from-file"
    assert os.environ.get("MIKU_TEST_OVERRIDE") == "from-shell"
