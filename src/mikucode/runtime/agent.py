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
                if action.summary:
                    state.record_observation(
                        ToolResult(
                            ok=True,
                            tool="final_answer",
                            summary=action.summary,
                        )
                    )
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
        """Parse model output into AgentAction with resilient fallbacks.

        Models (especially free chat models) often return plain text or JSON
        without a ``type`` field. For interactive usability we:
        - strip optional markdown code fences
        - accept valid AgentAction JSON as-is
        - map missing-type JSON / plain text to ``final_answer``
        """
        raw = content if content is not None else ""
        text = _strip_markdown_fence(raw.strip())
        if not text:
            return AgentAction(type="final_answer", summary="(empty model response)")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return AgentAction(type="final_answer", summary=raw.strip())

        if not isinstance(data, dict):
            return AgentAction(type="final_answer", summary=str(data))

        if "type" not in data:
            summary = _coerce_summary_from_dict(data)
            return AgentAction(type="final_answer", summary=summary)

        data = _normalize_action_dict(data)

        try:
            return AgentAction.model_validate(data)
        except Exception:
            # Malformed action object: surface text rather than crashing the REPL.
            summary = _coerce_summary_from_dict(data) or text[:2000]
            return AgentAction(type="final_answer", summary=summary)


def _strip_markdown_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if not lines:
        return text
    # Drop opening ``` or ```json
    lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _normalize_action_dict(data: dict) -> dict:
    """Fix common model mistakes before AgentAction validation.

    Models often emit a flattened patch_proposal like::

        {"type":"patch_proposal","kind":"search_replace","path":"...","old_text":"...","new_text":"..."}

    while the protocol requires a non-empty ``patches`` list.
    """
    normalized = dict(data)
    action_type = normalized.get("type")

    if action_type == "patch_proposal":
        patches = normalized.get("patches")
        if not patches:
            patch: dict = {}
            for key in (
                "kind",
                "path",
                "old_text",
                "new_text",
                "content",
                "if_exists",
            ):
                if key in normalized and normalized[key] is not None:
                    patch[key] = normalized[key]
            if patch.get("kind") or patch.get("path"):
                if "kind" not in patch and (
                    "old_text" in patch or "new_text" in patch
                ):
                    patch["kind"] = "search_replace"
                if "kind" not in patch and "content" in patch:
                    patch["kind"] = "create_file"
                normalized["patches"] = [patch]
                # Drop flattened keys so they are not confused with action fields.
                for key in list(patch.keys()):
                    normalized.pop(key, None)

    if action_type == "tool_call":
        # Sometimes models put tool args at top level instead of arguments{}.
        arguments = normalized.get("arguments")
        if not arguments or not isinstance(arguments, dict) or arguments == {}:
            known = {
                "type",
                "tool",
                "arguments",
                "reason",
                "summary",
                "patches",
                "question",
                "options",
                "items",
                "risk_level",
                "changed_files",
                "verification",
                "remaining_risks",
            }
            lifted = {
                key: value
                for key, value in normalized.items()
                if key not in known and value is not None
            }
            if lifted:
                normalized["arguments"] = lifted

    return normalized


def _coerce_summary_from_dict(data: dict) -> str:
    for key in ("summary", "content", "message", "text", "answer", "reply"):
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    return json.dumps(data, ensure_ascii=False)

