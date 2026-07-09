import json
import os
import time
from pathlib import Path

from mikucode.cli.factory import build_provider, build_registry
from mikucode.models.mock import MockProvider
from mikucode.runtime.agent import AgentRuntime


def run_smoke_benchmark(project_root: Path) -> dict:
    started = time.perf_counter()
    root = project_root.resolve()
    task_root = root / "bench-smoke-repo"
    task_root.mkdir(parents=True, exist_ok=True)
    (task_root / "hello.txt").write_text("hello", encoding="utf-8")

    if os.getenv("MIKU_MOCK_RESPONSES"):
        provider = build_provider()
    else:
        # Deterministic default mock so `miku bench smoke` works without API keys.
        provider = MockProvider(
            responses=[
                json.dumps(
                    {
                        "type": "tool_call",
                        "tool": "read_file",
                        "arguments": {"path": "hello.txt"},
                        "reason": "Read hello.txt",
                    }
                ),
                json.dumps({"type": "final_answer", "summary": "done"}),
            ]
        )

    runtime = AgentRuntime(
        project_root=task_root,
        provider=provider,
        registry=build_registry(task_root),
        max_steps=5,
    )
    state = runtime.run("Read hello.txt and finish.")
    duration = time.perf_counter() - started
    return {
        "tasks": 1,
        "passed": 1 if state.done else 0,
        "failed": 0 if state.done else 1,
        "steps": state.step_count,
        "duration_seconds": round(duration, 3),
    }
