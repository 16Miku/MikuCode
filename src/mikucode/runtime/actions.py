from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ActionType = Literal["tool_call", "patch_proposal", "plan_update", "ask_user", "final_answer"]


class AgentAction(BaseModel):
    type: ActionType
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    patches: list[dict[str, Any]] = Field(default_factory=list)
    reason: str | None = None
    summary: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    verification: list[dict[str, Any]] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    items: list[dict[str, str]] = Field(default_factory=list)
    question: str | None = None
    options: list[str] = Field(default_factory=list)
    risk_level: str | None = None

    @model_validator(mode="after")
    def validate_by_type(self) -> "AgentAction":
        if self.type == "tool_call" and not self.tool:
            raise ValueError("tool is required for tool_call")
        if self.type == "patch_proposal" and not self.patches:
            raise ValueError("patches are required for patch_proposal")
        if self.type == "ask_user" and not self.question:
            raise ValueError("question is required for ask_user")
        if self.type == "final_answer" and not self.summary:
            raise ValueError("summary is required for final_answer")
        return self


class ToolResult(BaseModel):
    ok: bool
    tool: str
    summary: str
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
