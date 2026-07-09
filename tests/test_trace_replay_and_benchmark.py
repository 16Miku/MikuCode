import json
from pathlib import Path

from mikucode.benchmark.smoke import run_smoke_benchmark
from mikucode.tracing.replay import render_trace


def test_render_trace_summarizes_events(tmp_path: Path):
    trace = tmp_path / "session.jsonl"
    trace.write_text(
        "\n".join(
            [
                json.dumps({"type": "user_task", "payload": {"task": "fix tests"}}),
                json.dumps(
                    {
                        "type": "tool_result",
                        "payload": {"tool": "run_tests", "summary": "failed"},
                    }
                ),
                json.dumps({"type": "final_report", "payload": {"summary": "done"}}),
            ]
        ),
        encoding="utf-8",
    )

    rendered = render_trace(trace)

    assert "user_task" in rendered
    assert "run_tests" in rendered
    assert "done" in rendered


def test_smoke_benchmark_returns_metrics(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(
        "MIKU_MOCK_RESPONSES",
        '[{"type":"final_answer","summary":"done"}]',
    )

    result = run_smoke_benchmark(tmp_path)

    assert result["tasks"] >= 1
    assert "passed" in result
    assert "duration_seconds" in result
