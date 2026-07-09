from mikucode.models.base import ModelResponse


class MockProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.index = 0

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> ModelResponse:
        del messages, tools
        if self.index >= len(self.responses):
            return ModelResponse(
                content='{"type":"final_answer","summary":"No more mock responses."}'
            )
        content = self.responses[self.index]
        self.index += 1
        return ModelResponse(content=content)
