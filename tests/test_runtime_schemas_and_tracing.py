import json
from pathlib import Path

from mikucode.runtime.actions import AgentAction, ToolResult
from mikucode.runtime.events import AgentEvent
from mikucode.runtime.state import AgentState
from mikucode.tracing.recorder import TraceRecorder, redact_secrets


def test_agent_action_validates_tool_call():
    action = AgentAction.model_validate(
        {
            "type": "tool_call",
            "tool": "read_file",
            "arguments": {"path": "src/example.py"},
            "reason": "Read the implementation.",
        }
    )

    assert action.type == "tool_call"
    assert action.tool == "read_file"
    assert action.arguments["path"] == "src/example.py"


def test_agent_action_rejects_missing_tool_for_tool_call():
    try:
        AgentAction.model_validate({"type": "tool_call", "arguments": {}})
    except ValueError as exc:
        assert "tool" in str(exc)
    else:
        raise AssertionError("Expected validation failure")


def test_tool_result_has_structured_metadata():
    result = ToolResult(ok=True, tool="run_tests", summary="12 passed", metadata={"exit_code": 0})

    assert result.ok is True
    assert result.metadata["exit_code"] == 0


def test_trace_recorder_writes_redacted_jsonl(tmp_path: Path):
    recorder = TraceRecorder(tmp_path)
    event = AgentEvent(type="tool_result", step=1, payload={"content": "OPENAI_API_KEY=sk-secret"})

    recorder.record(event)

    lines = recorder.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["type"] == "tool_result"
    assert "sk-secret" not in lines[0]
    assert "[REDACTED]" in lines[0]


def test_agent_state_tracks_steps_and_observations():
    state = AgentState.new(task="fix tests")
    state.record_observation(ToolResult(ok=True, tool="search_text", summary="found parser"))

    assert state.task == "fix tests"
    assert state.step_count == 0
    assert len(state.observations) == 1


def test_redact_secrets_handles_bearer_tokens():
    text = "Authorization: Bearer abc.def.ghi"

    assert redact_secrets(text) == "Authorization: Bearer [REDACTED]"
