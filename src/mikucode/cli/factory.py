import json
import os
from pathlib import Path

from mikucode.models.base import ModelProvider
from mikucode.models.mock import MockProvider
from mikucode.models.openai_compatible import OpenAICompatibleProvider
from mikucode.tools.filesystem import register_filesystem_tools
from mikucode.tools.registry import ToolRegistry
from mikucode.tools.search import register_search_tools
from mikucode.tools.shell import register_shell_tool
from mikucode.tools.testing import register_testing_tools


def build_registry(project_root: Path) -> ToolRegistry:
    registry = ToolRegistry()
    register_filesystem_tools(registry, project_root)
    register_search_tools(registry, project_root)
    register_shell_tool(registry, project_root)
    register_testing_tools(registry, project_root)
    return registry


def build_provider() -> ModelProvider:
    mock = os.getenv("MIKU_MOCK_RESPONSES")
    if mock:
        encoded = json.loads(mock)
        responses = [
            json.dumps(item) if isinstance(item, dict) else str(item) for item in encoded
        ]
        return MockProvider(responses=responses)
    return OpenAICompatibleProvider()
