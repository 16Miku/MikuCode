import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def create_backup(project_root: Path, relative_path: str) -> Path:
    source = project_root / relative_path
    patch_id = datetime.now(UTC).strftime("patch-%Y%m%dT%H%M%SZ")
    backup_root = project_root / ".miku" / "backups" / patch_id
    target = backup_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    manifest = project_root / ".miku" / "backups" / "last.json"
    manifest.write_text(
        json.dumps({"patch_id": patch_id, "files": [relative_path]}),
        encoding="utf-8",
    )
    return backup_root
