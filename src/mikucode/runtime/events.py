from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    type: str
    step: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload: dict[str, Any] = Field(default_factory=dict)
