import re
from datetime import UTC, datetime
from pathlib import Path

from mikucode.runtime.events import AgentEvent

# Value side stops before whitespace and JSON string delimiters so
# serialize→redact on model_dump_json() leaves a still-parseable JSONL line.
_SECRET_PATTERNS = [
    re.compile(r"OPENAI_API_KEY=[^\s\"']+"),
    re.compile(r"ANTHROPIC_API_KEY=[^\s\"']+"),
    re.compile(r"Authorization:\s*Bearer\s+[^\s\"']+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"api_key=[^\s\"']+", re.IGNORECASE),
    re.compile(r"token=[^\s\"']+", re.IGNORECASE),
    re.compile(r"password=[^\s\"']+", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        if pattern.pattern.startswith("Authorization"):
            redacted = pattern.sub("Authorization: Bearer [REDACTED]", redacted)
        else:
            redacted = pattern.sub(
                lambda match: match.group(0).split("=")[0] + "=[REDACTED]"
                if "=" in match.group(0)
                else "[REDACTED]",
                redacted,
            )
    return redacted


class TraceRecorder:
    def __init__(self, miku_dir: Path) -> None:
        sessions_dir = miku_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.path = sessions_dir / f"{timestamp}-session.jsonl"

    def record(self, event: AgentEvent) -> None:
        raw = event.model_dump_json()
        redacted = redact_secrets(raw)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(redacted + "\n")
