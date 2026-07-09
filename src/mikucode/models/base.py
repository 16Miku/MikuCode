from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelResponse:
    content: str


class ModelProvider(Protocol):
    def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> ModelResponse:
        ...
