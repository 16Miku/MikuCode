from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from mikucode.runtime.actions import ToolResult


ToolExecutor = Callable[[dict[str, Any]], ToolResult]


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    permission: str = "auto"
    timeout: int = 5
    output_limit: int = 20_000
