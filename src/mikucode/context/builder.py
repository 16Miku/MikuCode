import json
from pathlib import Path

from mikucode.context.file_tree import build_file_tree
from mikucode.memory.store import MemoryStore
from mikucode.runtime.state import AgentState


class ContextBuilder:
    def __init__(self, project_root: Path, max_context_chars: int = 60_000) -> None:
        self.project_root = project_root.resolve()
        self.max_context_chars = max_context_chars
        self.memory = MemoryStore(self.project_root)

    def build(self, state: AgentState) -> list[dict]:
        observations = [obs.model_dump() for obs in state.observations[-5:]]
        content = {
            "task": state.task,
            "project_memory": self.memory.read_project_memory(),
            "file_tree": build_file_tree(self.project_root),
            "recent_observations": observations,
            "verification_state": state.verification_state,
        }
        serialized = json.dumps(content, ensure_ascii=False)
        if len(serialized) > self.max_context_chars:
            serialized = serialized[: self.max_context_chars] + "\n[context truncated]"
        return [
            {
                "role": "system",
                "content": "You are MikuCode. Return exactly one JSON AgentAction.",
            },
            {"role": "user", "content": state.task},
            {"role": "system", "content": serialized},
        ]
