from pydantic import BaseModel, Field

from mikucode.runtime.actions import ToolResult


class AgentState(BaseModel):
    task: str
    step_count: int = 0
    done: bool = False
    observations: list[ToolResult] = Field(default_factory=list)
    files_read: set[str] = Field(default_factory=set)
    files_modified: set[str] = Field(default_factory=set)
    verification_state: str = "unknown"

    @classmethod
    def new(cls, task: str) -> "AgentState":
        return cls(task=task)

    def next_step(self) -> None:
        self.step_count += 1

    def record_observation(self, result: ToolResult) -> None:
        self.observations.append(result)
