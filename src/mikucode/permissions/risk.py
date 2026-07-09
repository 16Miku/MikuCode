from dataclasses import dataclass


@dataclass(frozen=True)
class CommandRisk:
    level: str
    decision: str
    reasons: list[str]


def classify_command(command: str) -> CommandRisk:
    lowered = command.lower()
    if (
        "| bash" in lowered
        or "| sh" in lowered
        or "sudo" in lowered
        or "iex" in lowered
        or "invoke-webrequest" in lowered
        or "runas" in lowered
    ):
        return CommandRisk(
            level="critical",
            decision="deny",
            reasons=["critical shell pattern"],
        )
    if "rm -rf /" in lowered or "git reset --hard" in lowered or "git clean" in lowered:
        return CommandRisk(
            level="critical",
            decision="deny",
            reasons=["destructive command"],
        )
    medium_patterns = [
        "uv sync",
        "uv add",
        "pip install",
        "npm install",
        "pnpm install",
        "cargo install",
    ]
    if any(pattern in lowered for pattern in medium_patterns):
        return CommandRisk(
            level="medium",
            decision="ask",
            reasons=["dependency or environment mutation"],
        )
    low_patterns = [
        "uv run pytest",
        "python -m pytest",
        "pytest",
        "ruff check",
        "mypy",
        "git status",
        "git diff",
        "git log",
        "python -c",
    ]
    if any(pattern in lowered for pattern in low_patterns):
        return CommandRisk(
            level="low",
            decision="allow",
            reasons=["inspection or verification command"],
        )
    return CommandRisk(
        level="medium",
        decision="ask",
        reasons=["unclassified command"],
    )
