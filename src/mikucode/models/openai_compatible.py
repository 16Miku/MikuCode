import os

import httpx

from mikucode.models.base import ModelResponse


class OpenAICompatibleProvider:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("MIKU_OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self.api_key = (
            api_key or os.getenv("MIKU_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        )
        self.model = model or os.getenv("MIKU_MODEL") or "gpt-4o-mini"

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> ModelResponse:
        del tools
        if not self.api_key:
            raise RuntimeError(
                "Missing API key. Set MIKU_OPENAI_API_KEY or OPENAI_API_KEY."
            )
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages, "temperature": 0},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return ModelResponse(content=data["choices"][0]["message"]["content"])
