import json
from pathlib import Path

from mikucode.config import ensure_miku_dir
from mikucode.context.builder import ContextBuilder
from mikucode.models.base import ModelProvider
from mikucode.runtime.actions import AgentAction, ToolResult
from mikucode.runtime.events import AgentEvent
from mikucode.runtime.state import AgentState
from mikucode.tools.registry import ToolRegistry
from mikucode.tracing.recorder import TraceRecorder


class AgentRuntime:
    def __init__(
        self,
        project_root: Path,
        provider: ModelProvider,
        registry: ToolRegistry,
        max_steps: int = 20,
    ) -> None:
        self.project_root = project_root.resolve()
        self.provider = provider
        self.registry = registry
        self.max_steps = max_steps
        self.recorder = TraceRecorder(ensure_miku_dir(self.project_root))

    def run(self, task: str) -> AgentState:
        state = AgentState.new(task)
        self.recorder.record(AgentEvent(type="session_started", payload={"task": task}))
        while not state.done:
            if state.step_count >= self.max_steps:
                result = ToolResult(
                    ok=False,
                    tool="runtime",
                    summary="Stopped because max_steps was reached",
                )
                state.record_observation(result)
                self.recorder.record(
                    AgentEvent(
                        type="session_stopped",
                        step=state.step_count,
                        payload=result.model_dump(),
                    )
                )
                return state

            response = self.provider.complete(
                messages=self._build_messages(state), tools=None
            )
            action = self._parse_action(response.content)
            state.next_step()
            self.recorder.record(
                AgentEvent(
                    type="action_parsed",
                    step=state.step_count,
                    payload=action.model_dump(),
                )
            )

            if action.type == "final_answer":
                state.done = True
                self.recorder.record(
                    AgentEvent(
                        type="final_report",
                        step=state.step_count,
                        payload=action.model_dump(),
                    )
                )
                return state

            if action.type == "tool_call":
                result = self.registry.execute(action.tool or "", action.arguments)
                state.record_observation(result)
                self.recorder.record(
                    AgentEvent(
                        type="tool_result",
                        step=state.step_count,
                        payload=result.model_dump(),
                    )
                )
                continue

            if action.type == "patch_proposal":
                from mikucode.editing.patch import PatchEngine

                result = PatchEngine(self.project_root).apply_patches(action.patches)
                state.record_observation(result)
                if result.ok:
                    for changed_file in result.metadata.get("changed_files", []):
                        state.files_modified.add(changed_file)
                    state.verification_state = "stale"
                self.recorder.record(
                    AgentEvent(
                        type="patch_applied",
                        step=state.step_count,
                        payload=result.model_dump(),
                    )
                )
                continue

            result = ToolResult(
                ok=False,
                tool="runtime",
                summary=f"Unsupported action type in this task: {action.type}",
            )
            state.record_observation(result)
            self.recorder.record(
                AgentEvent(
                    type="validation_failed",
                    step=state.step_count,
                    payload=result.model_dump(),
                )
            )

        return state

    def _build_messages(self, state: AgentState) -> list[dict]:
        return ContextBuilder(self.project_root).build(state)

    def _parse_action(self, content: str) -> AgentAction:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model returned invalid JSON: {content}") from exc
        return AgentAction.model_validate(data)
