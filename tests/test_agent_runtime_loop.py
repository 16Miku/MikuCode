from pathlib import Path

from mikucode.models.mock import MockProvider
from mikucode.runtime.agent import AgentRuntime
from mikucode.tools.filesystem import register_filesystem_tools
from mikucode.tools.registry import ToolRegistry


def test_runtime_executes_tool_call_then_final_answer(tmp_path: Path):
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    provider = MockProvider(
        responses=[
            '{"type":"tool_call","tool":"read_file","arguments":{"path":"hello.txt"},"reason":"Read file"}',
            '{"type":"final_answer","summary":"Read the file successfully."}',
        ]
    )
    runtime = AgentRuntime(
        project_root=tmp_path, provider=provider, registry=registry, max_steps=5
    )

    state = runtime.run("read hello")

    assert state.done is True
    assert state.observations[0].tool == "read_file"
    assert state.observations[0].ok is True
    assert state.step_count == 2


def test_runtime_stops_at_max_steps(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    provider = MockProvider(
        responses=[
            '{"type":"tool_call","tool":"list_files","arguments":{},"reason":"List files"}',
            '{"type":"tool_call","tool":"list_files","arguments":{},"reason":"List files again"}',
        ]
    )
    runtime = AgentRuntime(
        project_root=tmp_path, provider=provider, registry=registry, max_steps=1
    )

    state = runtime.run("loop")

    assert state.done is False
    assert state.step_count == 1
    assert state.observations[-1].summary == "Stopped because max_steps was reached"


def test_runtime_records_trace(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    provider = MockProvider(responses=['{"type":"final_answer","summary":"done"}'])
    runtime = AgentRuntime(
        project_root=tmp_path, provider=provider, registry=registry, max_steps=3
    )

    runtime.run("finish")

    trace_files = list((tmp_path / ".miku" / "sessions").glob("*.jsonl"))
    assert trace_files
    assert "final_report" in trace_files[0].read_text(encoding="utf-8")


def test_mock_provider_out_of_bounds_returns_final_answer():
    provider = MockProvider(responses=[])

    response = provider.complete(messages=[{"role": "user", "content": "hi"}])

    assert "final_answer" in response.content
    assert "No more mock responses." in response.content


def test_runtime_unsupported_action_type_continues(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    provider = MockProvider(
        responses=[
            '{"type":"ask_user","question":"What next?"}',
            '{"type":"final_answer","summary":"finished after unsupported"}',
        ]
    )
    runtime = AgentRuntime(
        project_root=tmp_path, provider=provider, registry=registry, max_steps=5
    )

    state = runtime.run("ask something")

    assert state.done is True
    assert any(
        obs.summary.startswith("Unsupported action type in this task:")
        for obs in state.observations
    )
