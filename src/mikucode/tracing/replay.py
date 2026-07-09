import json
from pathlib import Path


def render_trace(path: Path) -> str:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        event = json.loads(raw)
        event_type = str(event.get("type", "unknown"))
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        pieces: list[str] = []
        if payload.get("tool"):
            pieces.append(str(payload["tool"]))
        detail = payload.get("summary") or payload.get("task")
        if detail:
            pieces.append(str(detail))
        if pieces:
            lines.append(f"{event_type}: {' '.join(pieces)}")
        else:
            lines.append(event_type)
    return "\n".join(lines)
