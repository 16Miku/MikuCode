# MikuCode B-Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MikuCode, a Python + `uv` local coding agent runtime that can run in REPL and one-shot CLI modes, call an OpenAI-compatible model through a JSON action protocol, execute permissioned tools, propose patch-based edits, run verification, and record replayable traces.

**Architecture:** MikuCode treats the LLM as a decision engine, not an executor. The model emits structured `AgentAction` objects; the runtime validates them, applies permission policy, executes tools or patch workflows, records JSONL traces, and assembles verification-grounded reports. The B version keeps Web dashboard, Docker sandbox, full MCP, IDE extension, and autonomous multi-agent execution out of the implementation path.

**Tech Stack:** Python `>=3.11`, `uv`, Typer, Rich, Pydantic, HTTPX, pytest, ruff.

## Global Constraints

- Use Python `>=3.11`.
- Manage all Python commands and dependencies with `uv`.
- Package name: `mikucode`.
- CLI command name: `miku`.
- Model layer is OpenAI-compatible first.
- Default model interaction is JSON command mode.
- REPL is the primary interaction mode; one-shot CLI is also required.
- B version implements developer-safety guardrails, not a hardened adversarial sandbox.
- B version must not implement Web dashboard, full MCP protocol, Docker sandbox, IDE extension, or autonomous parallel multi-agent execution.
- File edits must use patch proposal, diff preview, backup, and undo; direct model-driven `write_file` is not part of the default exposed tool set.
- Final reports must be grounded in runtime evidence: changed files, commands, exit codes, verification summaries, and trace path.

---

## File Structure Map

Create this structure across the tasks. Do not create C-version files unless a B-version task explicitly needs an interface stub.

```text
pyproject.toml
README.md
.gitignore
src/mikucode/__init__.py
src/mikucode/cli/main.py
src/mikucode/cli/repl.py
src/mikucode/config.py
src/mikucode/runtime/actions.py
src/mikucode/runtime/agent.py
src/mikucode/runtime/state.py
src/mikucode/runtime/events.py
src/mikucode/models/base.py
src/mikucode/models/mock.py
src/mikucode/models/openai_compatible.py
src/mikucode/tools/base.py
src/mikucode/tools/registry.py
src/mikucode/tools/filesystem.py
src/mikucode/tools/search.py
src/mikucode/tools/shell.py
src/mikucode/tools/testing.py
src/mikucode/permissions/policy.py
src/mikucode/permissions/risk.py
src/mikucode/editing/patch.py
src/mikucode/editing/diff.py
src/mikucode/editing/backup.py
src/mikucode/editing/undo.py
src/mikucode/context/builder.py
src/mikucode/context/file_tree.py
src/mikucode/memory/store.py
src/mikucode/tracing/recorder.py
src/mikucode/tracing/replay.py
src/mikucode/verification/detector.py
src/mikucode/verification/runner.py
src/mikucode/verification/report.py
src/mikucode/benchmark/smoke.py
tests/
```

Responsibility boundaries:

- `cli/`: user-facing commands and REPL only.
- `runtime/`: loop, state, actions, events.
- `models/`: provider interface and concrete providers.
- `tools/`: schema-validated tool implementations.
- `permissions/`: path and command safety decisions.
- `editing/`: patch validation, diff, backup, undo.
- `context/`: bounded prompt/context assembly.
- `memory/`: project and session memory persistence.
- `tracing/`: JSONL event recording and replay.
- `verification/`: test command detection, execution, report evidence.
- `benchmark/`: small deterministic smoke benchmark harness.

---

### Task 1: Project Skeleton, CLI Entrypoint, and `.miku` Initialization

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/mikucode/__init__.py`
- Create: `src/mikucode/config.py`
- Create: `src/mikucode/cli/main.py`
- Create: `src/mikucode/cli/repl.py`
- Test: `tests/test_cli_init.py`

**Interfaces:**
- Produces: `MikuConfig`, `load_config(project_root: Path) -> MikuConfig`, `ensure_miku_dir(project_root: Path) -> Path`, Typer app `app`.
- Consumes: none.

- [ ] **Step 1: Create the Python project metadata**

Write `pyproject.toml`:

```toml
[project]
name = "mikucode"
version = "0.1.0"
description = "Local coding agent runtime inspired by Claude Code/Codex"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "typer>=0.12.0",
  "rich>=13.7.0",
  "pydantic>=2.7.0",
  "httpx>=0.27.0",
]

[project.scripts]
miku = "mikucode.cli.main:app"

[dependency-groups]
dev = [
  "pytest>=8.2.0",
  "ruff>=0.5.0",
]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Write `.gitignore`:

```gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.miku/
dist/
build/
*.egg-info/
```

- [ ] **Step 2: Write the failing CLI initialization test**

Create `tests/test_cli_init.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from mikucode.cli.main import app


def test_init_creates_miku_project_files(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / ".miku").is_dir()
    assert (tmp_path / ".miku" / "project.md").is_file()
    assert (tmp_path / ".miku" / "config.toml").is_file()
    assert (tmp_path / ".miku" / "sessions").is_dir()
    assert "Initialized MikuCode" in result.stdout


def test_chat_command_starts_and_exits(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(app, ["chat", "--project-root", str(tmp_path)], input="/exit\n")

    assert result.exit_code == 0
    assert "MikuCode" in result.stdout
```

- [ ] **Step 3: Run the failing test**

Run:

```bash
uv sync
uv run pytest tests/test_cli_init.py -v
```

Expected: FAIL because `mikucode.cli.main` does not exist.

- [ ] **Step 4: Implement config and CLI initialization**

Create `src/mikucode/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/mikucode/config.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MikuConfig:
    project_root: Path
    miku_dir: Path
    permission_mode: str = "auto-safe"
    default_test_command: str = "uv run pytest"


def ensure_miku_dir(project_root: Path) -> Path:
    root = project_root.resolve()
    miku_dir = root / ".miku"
    (miku_dir / "sessions").mkdir(parents=True, exist_ok=True)
    (miku_dir / "patches").mkdir(parents=True, exist_ok=True)
    (miku_dir / "backups").mkdir(parents=True, exist_ok=True)

    project_md = miku_dir / "project.md"
    if not project_md.exists():
        project_md.write_text(
            "# MikuCode Project Memory\n\n"
            "## Commands\n"
            "- Test: uv run pytest\n\n"
            "## Conventions\n"
            "- Do not edit generated files.\n",
            encoding="utf-8",
        )

    config_toml = miku_dir / "config.toml"
    if not config_toml.exists():
        config_toml.write_text(
            "permission_mode = \"auto-safe\"\n\n"
            "[verification]\n"
            "test_command = \"uv run pytest\"\n",
            encoding="utf-8",
        )

    return miku_dir


def load_config(project_root: Path) -> MikuConfig:
    root = project_root.resolve()
    miku_dir = ensure_miku_dir(root)
    return MikuConfig(project_root=root, miku_dir=miku_dir)
```

Create `src/mikucode/cli/repl.py`:

```python
from pathlib import Path

from rich.console import Console

from mikucode.config import load_config


class MikuRepl:
    def __init__(self, project_root: Path, console: Console | None = None) -> None:
        self.config = load_config(project_root)
        self.console = console or Console()

    def run(self) -> None:
        self.console.print("[bold cyan]MikuCode[/bold cyan] interactive REPL")
        while True:
            try:
                user_input = input("MikuCode > ").strip()
            except EOFError:
                self.console.print("Goodbye.")
                return
            if user_input in {"/exit", "exit", "quit"}:
                self.console.print("Goodbye.")
                return
            if not user_input:
                continue
            self.console.print("Runtime is not connected yet. This command will be handled in Task 8.")
```

Create `src/mikucode/cli/main.py`:

```python
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from mikucode.cli.repl import MikuRepl
from mikucode.config import ensure_miku_dir

app = typer.Typer(help="MikuCode local coding agent runtime")
console = Console()


@app.command()
def init(project_root: Path = typer.Option(Path.cwd(), help="Project root to initialize")) -> None:
    miku_dir = ensure_miku_dir(project_root)
    console.print(f"Initialized MikuCode at [bold]{miku_dir}[/bold]")


@app.command()
def chat(project_root: Path = typer.Option(Path.cwd(), help="Project root for the REPL")) -> None:
    repl = MikuRepl(project_root=project_root, console=console)
    repl.run()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    task: Optional[str] = typer.Argument(None, help="One-shot task for MikuCode"),
    project_root: Path = typer.Option(Path.cwd(), help="Project root"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if task is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)
    ensure_miku_dir(project_root)
    console.print(f"One-shot runtime is not connected yet. Task received: {task}")
```

- [ ] **Step 5: Run tests and lint**

Run:

```bash
uv run pytest tests/test_cli_init.py -v
uv run ruff check src tests
```

Expected: PASS for tests and ruff.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore README.md src tests
git commit -m "feat: scaffold mikucode cli"
```

---

### Task 2: Runtime Schemas, Events, and JSONL Trace Recorder

**Files:**
- Create: `src/mikucode/runtime/actions.py`
- Create: `src/mikucode/runtime/events.py`
- Create: `src/mikucode/runtime/state.py`
- Create: `src/mikucode/tracing/recorder.py`
- Test: `tests/test_runtime_schemas_and_tracing.py`

**Interfaces:**
- Consumes: `MikuConfig.miku_dir` from Task 1.
- Produces: `AgentAction`, `ToolResult`, `AgentState`, `TraceRecorder.record(event: AgentEvent) -> None`, `redact_secrets(text: str) -> str`.

- [ ] **Step 1: Write failing schema and trace tests**

Create `tests/test_runtime_schemas_and_tracing.py`:

```python
import json
from pathlib import Path

from mikucode.runtime.actions import AgentAction, ToolResult
from mikucode.runtime.events import AgentEvent
from mikucode.runtime.state import AgentState
from mikucode.tracing.recorder import TraceRecorder, redact_secrets


def test_agent_action_validates_tool_call():
    action = AgentAction.model_validate(
        {
            "type": "tool_call",
            "tool": "read_file",
            "arguments": {"path": "src/example.py"},
            "reason": "Read the implementation.",
        }
    )

    assert action.type == "tool_call"
    assert action.tool == "read_file"
    assert action.arguments["path"] == "src/example.py"


def test_agent_action_rejects_missing_tool_for_tool_call():
    try:
        AgentAction.model_validate({"type": "tool_call", "arguments": {}})
    except ValueError as exc:
        assert "tool" in str(exc)
    else:
        raise AssertionError("Expected validation failure")


def test_tool_result_has_structured_metadata():
    result = ToolResult(ok=True, tool="run_tests", summary="12 passed", metadata={"exit_code": 0})

    assert result.ok is True
    assert result.metadata["exit_code"] == 0


def test_trace_recorder_writes_redacted_jsonl(tmp_path: Path):
    recorder = TraceRecorder(tmp_path)
    event = AgentEvent(type="tool_result", step=1, payload={"content": "OPENAI_API_KEY=sk-secret"})

    recorder.record(event)

    lines = recorder.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["type"] == "tool_result"
    assert "sk-secret" not in lines[0]
    assert "[REDACTED]" in lines[0]


def test_agent_state_tracks_steps_and_observations():
    state = AgentState.new(task="fix tests")
    state.record_observation(ToolResult(ok=True, tool="search_text", summary="found parser"))

    assert state.task == "fix tests"
    assert state.step_count == 0
    assert len(state.observations) == 1


def test_redact_secrets_handles_bearer_tokens():
    text = "Authorization: Bearer abc.def.ghi"

    assert redact_secrets(text) == "Authorization: Bearer [REDACTED]"
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_runtime_schemas_and_tracing.py -v
```

Expected: FAIL because runtime and tracing modules do not exist.

- [ ] **Step 3: Implement runtime schemas**

Create `src/mikucode/runtime/actions.py`:

```python
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
```

Create `src/mikucode/runtime/events.py`:

```python
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    type: str
    step: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload: dict[str, Any] = Field(default_factory=dict)
```

Create `src/mikucode/runtime/state.py`:

```python
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
```

- [ ] **Step 4: Implement trace recorder and redaction**

Create `src/mikucode/tracing/recorder.py`:

```python
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from mikucode.runtime.events import AgentEvent

_SECRET_PATTERNS = [
    re.compile(r"OPENAI_API_KEY=\S+"),
    re.compile(r"ANTHROPIC_API_KEY=\S+"),
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"api_key=\S+", re.IGNORECASE),
    re.compile(r"token=\S+", re.IGNORECASE),
    re.compile(r"password=\S+", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        if pattern.pattern.startswith("Authorization"):
            redacted = pattern.sub("Authorization: Bearer [REDACTED]", redacted)
        else:
            redacted = pattern.sub(lambda match: match.group(0).split("=")[0] + "=[REDACTED]" if "=" in match.group(0) else "[REDACTED]", redacted)
    return redacted


class TraceRecorder:
    def __init__(self, miku_dir: Path) -> None:
        sessions_dir = miku_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.path = sessions_dir / f"{timestamp}-session.jsonl"

    def record(self, event: AgentEvent) -> None:
        raw = event.model_dump_json()
        redacted = redact_secrets(raw)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(redacted + "\n")
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_runtime_schemas_and_tracing.py -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/runtime src/mikucode/tracing tests/test_runtime_schemas_and_tracing.py
git commit -m "feat: add runtime schemas and tracing"
```

---

### Task 3: Tool Registry, Path Sandbox, Filesystem, and Search Tools

**Files:**
- Create: `src/mikucode/tools/base.py`
- Create: `src/mikucode/tools/registry.py`
- Create: `src/mikucode/tools/filesystem.py`
- Create: `src/mikucode/tools/search.py`
- Create: `src/mikucode/permissions/policy.py`
- Test: `tests/test_tools_filesystem_search.py`

**Interfaces:**
- Consumes: `ToolResult` from Task 2.
- Produces: `ToolDefinition`, `ToolRegistry`, `PathPolicy.ensure_inside_project(path: str) -> Path`, `register_filesystem_tools(registry, project_root)`, `register_search_tools(registry, project_root)`.

- [ ] **Step 1: Write failing tests for tools and path safety**

Create `tests/test_tools_filesystem_search.py`:

```python
from pathlib import Path

from mikucode.permissions.policy import PathPolicy
from mikucode.tools.filesystem import register_filesystem_tools
from mikucode.tools.registry import ToolRegistry
from mikucode.tools.search import register_search_tools


def test_path_policy_allows_project_file(tmp_path: Path):
    file_path = tmp_path / "src" / "main.py"
    file_path.parent.mkdir()
    file_path.write_text("print('hi')", encoding="utf-8")

    policy = PathPolicy(tmp_path)

    assert policy.ensure_inside_project("src/main.py") == file_path.resolve()


def test_path_policy_denies_escape(tmp_path: Path):
    policy = PathPolicy(tmp_path)

    try:
        policy.ensure_inside_project("../secret.txt")
    except PermissionError as exc:
        assert "outside project root" in str(exc)
    else:
        raise AssertionError("Expected path escape denial")


def test_path_policy_denies_secret_file(tmp_path: Path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-secret", encoding="utf-8")
    policy = PathPolicy(tmp_path)

    try:
        policy.ensure_inside_project(".env")
    except PermissionError as exc:
        assert "secret" in str(exc)
    else:
        raise AssertionError("Expected secret file denial")


def test_read_file_tool_reads_text_file(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("line1\nline2\n", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)

    result = registry.execute("read_file", {"path": "src/main.py"})

    assert result.ok is True
    assert "line1" in result.content
    assert result.metadata["path"] == "src/main.py"


def test_list_files_ignores_cache_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)

    result = registry.execute("list_files", {})

    assert "src/main.py" in result.content
    assert ".venv/ignored.py" not in result.content


def test_search_text_finds_matches(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "parser.py").write_text("def parse_config():\n    return {}\n", encoding="utf-8")
    registry = ToolRegistry()
    register_search_tools(registry, tmp_path)

    result = registry.execute("search_text", {"query": "parse_config"})

    assert result.ok is True
    assert "src/parser.py:1" in result.content
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_tools_filesystem_search.py -v
```

Expected: FAIL because tool modules do not exist.

- [ ] **Step 3: Implement base tool registry**

Create `src/mikucode/tools/base.py`:

```python
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
    timeout_seconds: int = 5
    output_limit_chars: int = 20_000
```

Create `src/mikucode/tools/registry.py`:

```python
from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition, ToolExecutor


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._executors: dict[str, ToolExecutor] = {}

    def register(self, definition: ToolDefinition, executor: ToolExecutor) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._definitions[definition.name] = definition
        self._executors[definition.name] = executor

    def definition(self, name: str) -> ToolDefinition:
        return self._definitions[name]

    def definitions(self) -> list[ToolDefinition]:
        return list(self._definitions.values())

    def execute(self, name: str, arguments: dict) -> ToolResult:
        if name not in self._executors:
            return ToolResult(ok=False, tool=name, summary=f"Unknown tool: {name}")
        return self._executors[name](arguments)
```

- [ ] **Step 4: Implement path policy and filesystem tools**

Create `src/mikucode/permissions/policy.py`:

```python
from pathlib import Path

_SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
_SECRET_SUFFIXES = {".pem", ".key"}
_ALLOWED_SECRET_EXAMPLES = {".env.example", ".env.sample"}


class PathPolicy:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def ensure_inside_project(self, path: str) -> Path:
        candidate = (self.project_root / path).resolve()
        if self.project_root not in candidate.parents and candidate != self.project_root:
            raise PermissionError(f"Path is outside project root: {path}")
        name = candidate.name
        if name not in _ALLOWED_SECRET_EXAMPLES and (
            name in _SECRET_NAMES or any(name.endswith(suffix) for suffix in _SECRET_SUFFIXES)
        ):
            raise PermissionError(f"Refusing to access secret-like file: {path}")
        if ".git" in candidate.parts and candidate.name != ".gitignore":
            raise PermissionError(f"Refusing to access .git internals: {path}")
        return candidate
```

Create `src/mikucode/tools/filesystem.py`:

```python
from pathlib import Path

from mikucode.permissions.policy import PathPolicy
from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry

_IGNORED_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}


def register_filesystem_tools(registry: ToolRegistry, project_root: Path) -> None:
    policy = PathPolicy(project_root)

    def read_file(arguments: dict) -> ToolResult:
        path = str(arguments["path"])
        try:
            resolved = policy.ensure_inside_project(path)
            content = resolved.read_text(encoding="utf-8")
        except Exception as exc:
            return ToolResult(ok=False, tool="read_file", summary=str(exc), metadata={"path": path})
        return ToolResult(
            ok=True,
            tool="read_file",
            summary=f"Read {path}",
            content=content[:20_000],
            metadata={"path": path, "truncated": len(content) > 20_000},
        )

    def list_files(arguments: dict) -> ToolResult:
        del arguments
        files: list[str] = []
        for item in project_root.rglob("*"):
            if any(part in _IGNORED_DIRS for part in item.relative_to(project_root).parts):
                continue
            if item.is_file():
                files.append(item.relative_to(project_root).as_posix())
        files.sort()
        return ToolResult(ok=True, tool="list_files", summary=f"Listed {len(files)} files", content="\n".join(files))

    registry.register(
        ToolDefinition(name="read_file", description="Read a UTF-8 text file inside the project root."),
        read_file,
    )
    registry.register(
        ToolDefinition(name="list_files", description="List project files excluding common generated directories."),
        list_files,
    )
```

- [ ] **Step 5: Implement search tool**

Create `src/mikucode/tools/search.py`:

```python
from pathlib import Path

from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry

_IGNORED_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}


def register_search_tools(registry: ToolRegistry, project_root: Path) -> None:
    def search_text(arguments: dict) -> ToolResult:
        query = str(arguments["query"])
        max_results = int(arguments.get("max_results", 50))
        matches: list[str] = []
        for item in project_root.rglob("*"):
            rel = item.relative_to(project_root)
            if any(part in _IGNORED_DIRS for part in rel.parts):
                continue
            if not item.is_file():
                continue
            try:
                lines = item.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for index, line in enumerate(lines, start=1):
                if query in line:
                    matches.append(f"{rel.as_posix()}:{index}: {line.strip()}")
                    if len(matches) >= max_results:
                        return ToolResult(ok=True, tool="search_text", summary=f"Found {len(matches)} matches", content="\n".join(matches))
        return ToolResult(ok=True, tool="search_text", summary=f"Found {len(matches)} matches", content="\n".join(matches))

    registry.register(
        ToolDefinition(name="search_text", description="Search text in UTF-8 files inside the project root."),
        search_text,
    )
```

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest tests/test_tools_filesystem_search.py -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/tools src/mikucode/permissions tests/test_tools_filesystem_search.py
git commit -m "feat: add filesystem and search tools"
```

---

### Task 4: JSON Action Parser, Mock Provider, and Agent Runtime Loop

**Files:**
- Create: `src/mikucode/models/base.py`
- Create: `src/mikucode/models/mock.py`
- Create: `src/mikucode/runtime/agent.py`
- Modify: `src/mikucode/cli/main.py`
- Test: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- Consumes: `AgentAction`, `ToolResult`, `AgentState`, `ToolRegistry`, `TraceRecorder`.
- Produces: `ModelProvider.complete(messages: list[dict], tools: list[dict] | None = None) -> ModelResponse`, `MockProvider`, `AgentRuntime.run(task: str) -> AgentState`.

- [ ] **Step 1: Write failing runtime loop tests**

Create `tests/test_agent_runtime_loop.py`:

```python
from pathlib import Path

from mikucode.models.mock import MockProvider
from mikucode.runtime.agent import AgentRuntime
from mikucode.tools.filesystem import register_filesystem_tools
from mikucode.tools.registry import ToolRegistry


def test_runtime_executes_tool_call_then_final_answer(tmp_path: Path):
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    provider = MockProvider(
        responses=[
            '{"type":"tool_call","tool":"read_file","arguments":{"path":"hello.txt"},"reason":"Read file"}',
            '{"type":"final_answer","summary":"Read the file successfully."}',
        ]
    )
    runtime = AgentRuntime(project_root=tmp_path, provider=provider, registry=registry, max_steps=5)

    state = runtime.run("read hello")

    assert state.done is True
    assert state.observations[0].tool == "read_file"
    assert state.observations[0].ok is True
    assert state.step_count == 2


def test_runtime_stops_at_max_steps(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    provider = MockProvider(
        responses=[
            '{"type":"tool_call","tool":"list_files","arguments":{},"reason":"List files"}',
            '{"type":"tool_call","tool":"list_files","arguments":{},"reason":"List files again"}',
        ]
    )
    runtime = AgentRuntime(project_root=tmp_path, provider=provider, registry=registry, max_steps=1)

    state = runtime.run("loop")

    assert state.done is False
    assert state.step_count == 1
    assert state.observations[-1].summary == "Stopped because max_steps was reached"


def test_runtime_records_trace(tmp_path: Path):
    registry = ToolRegistry()
    register_filesystem_tools(registry, tmp_path)
    provider = MockProvider(responses=['{"type":"final_answer","summary":"done"}'])
    runtime = AgentRuntime(project_root=tmp_path, provider=provider, registry=registry, max_steps=3)

    runtime.run("finish")

    trace_files = list((tmp_path / ".miku" / "sessions").glob("*.jsonl"))
    assert trace_files
    assert "final_report" in trace_files[0].read_text(encoding="utf-8")
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_agent_runtime_loop.py -v
```

Expected: FAIL because model provider and runtime loop are missing.

- [ ] **Step 3: Implement model provider and mock provider**

Create `src/mikucode/models/base.py`:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelResponse:
    content: str


class ModelProvider(Protocol):
    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> ModelResponse:
        raise NotImplementedError
```

Create `src/mikucode/models/mock.py`:

```python
from mikucode.models.base import ModelResponse


class MockProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.index = 0

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> ModelResponse:
        del messages, tools
        if self.index >= len(self.responses):
            return ModelResponse(content='{"type":"final_answer","summary":"No more mock responses."}')
        content = self.responses[self.index]
        self.index += 1
        return ModelResponse(content=content)
```

- [ ] **Step 4: Implement runtime loop**

Create `src/mikucode/runtime/agent.py`:

```python
import json
from pathlib import Path

from mikucode.config import ensure_miku_dir
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
                result = ToolResult(ok=False, tool="runtime", summary="Stopped because max_steps was reached")
                state.record_observation(result)
                self.recorder.record(AgentEvent(type="session_stopped", step=state.step_count, payload=result.model_dump()))
                return state

            response = self.provider.complete(messages=self._build_messages(state), tools=None)
            action = self._parse_action(response.content)
            state.next_step()
            self.recorder.record(AgentEvent(type="action_parsed", step=state.step_count, payload=action.model_dump()))

            if action.type == "final_answer":
                state.done = True
                self.recorder.record(AgentEvent(type="final_report", step=state.step_count, payload=action.model_dump()))
                return state

            if action.type == "tool_call":
                result = self.registry.execute(action.tool or "", action.arguments)
                state.record_observation(result)
                self.recorder.record(AgentEvent(type="tool_result", step=state.step_count, payload=result.model_dump()))
                continue

            result = ToolResult(ok=False, tool="runtime", summary=f"Unsupported action type in this task: {action.type}")
            state.record_observation(result)
            self.recorder.record(AgentEvent(type="validation_failed", step=state.step_count, payload=result.model_dump()))

        return state

    def _build_messages(self, state: AgentState) -> list[dict]:
        observations = [obs.model_dump() for obs in state.observations[-5:]]
        return [
            {"role": "system", "content": "Return exactly one JSON AgentAction."},
            {"role": "user", "content": state.task},
            {"role": "system", "content": json.dumps({"recent_observations": observations})},
        ]

    def _parse_action(self, content: str) -> AgentAction:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model returned invalid JSON: {content}") from exc
        return AgentAction.model_validate(data)
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_agent_runtime_loop.py -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/models src/mikucode/runtime/agent.py tests/test_agent_runtime_loop.py
git commit -m "feat: add json action runtime loop"
```

---

### Task 5: Patch Engine, Diff Preview, Backup, Undo, and Patch Permissions

**Files:**
- Create: `src/mikucode/editing/diff.py`
- Create: `src/mikucode/editing/backup.py`
- Create: `src/mikucode/editing/patch.py`
- Create: `src/mikucode/editing/undo.py`
- Modify: `src/mikucode/runtime/agent.py`
- Test: `tests/test_patch_engine.py`

**Interfaces:**
- Consumes: `AgentAction.patch_proposal`, `PathPolicy`.
- Produces: `SearchReplacePatch`, `CreateFilePatch`, `PatchEngine.apply_patches(patches: list[dict]) -> ToolResult`, `UndoManager.undo_last() -> ToolResult`.

- [ ] **Step 1: Write failing patch tests**

Create `tests/test_patch_engine.py`:

```python
from pathlib import Path

from mikucode.editing.patch import PatchEngine
from mikucode.editing.undo import UndoManager


def test_search_replace_patch_applies_and_creates_diff(tmp_path: Path):
    target = tmp_path / "src" / "parser.py"
    target.parent.mkdir()
    target.write_text("def parse(text):\n    return parse_raw(text)\n", encoding="utf-8")
    engine = PatchEngine(tmp_path)

    result = engine.apply_patches(
        [
            {
                "kind": "search_replace",
                "path": "src/parser.py",
                "old_text": "return parse_raw(text)",
                "new_text": "return parse_raw(text.strip())",
            }
        ]
    )

    assert result.ok is True
    assert "-    return parse_raw(text)" in result.content
    assert "+    return parse_raw(text.strip())" in result.content
    assert "text.strip()" in target.read_text(encoding="utf-8")
    assert list((tmp_path / ".miku" / "backups").rglob("parser.py"))


def test_search_replace_requires_unique_old_text(tmp_path: Path):
    target = tmp_path / "main.py"
    target.write_text("x = 1\nx = 1\n", encoding="utf-8")
    engine = PatchEngine(tmp_path)

    result = engine.apply_patches(
        [{"kind": "search_replace", "path": "main.py", "old_text": "x = 1", "new_text": "x = 2"}]
    )

    assert result.ok is False
    assert "exactly once" in result.summary
    assert target.read_text(encoding="utf-8") == "x = 1\nx = 1\n"


def test_create_file_fails_if_file_exists(tmp_path: Path):
    (tmp_path / "notes.md").write_text("existing", encoding="utf-8")
    engine = PatchEngine(tmp_path)

    result = engine.apply_patches(
        [{"kind": "create_file", "path": "notes.md", "content": "new"}]
    )

    assert result.ok is False
    assert "already exists" in result.summary


def test_undo_restores_last_patch(tmp_path: Path):
    target = tmp_path / "main.py"
    target.write_text("value = 1\n", encoding="utf-8")
    engine = PatchEngine(tmp_path)
    engine.apply_patches(
        [{"kind": "search_replace", "path": "main.py", "old_text": "value = 1", "new_text": "value = 2"}]
    )

    result = UndoManager(tmp_path).undo_last()

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "value = 1\n"
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_patch_engine.py -v
```

Expected: FAIL because editing modules do not exist.

- [ ] **Step 3: Implement diff and backup helpers**

Create `src/mikucode/editing/diff.py`:

```python
import difflib


def unified_diff(path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{path} before",
            tofile=f"{path} after",
        )
    )
```

Create `src/mikucode/editing/backup.py`:

```python
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def create_backup(project_root: Path, relative_path: str) -> Path:
    source = project_root / relative_path
    patch_id = datetime.now(UTC).strftime("patch-%Y%m%dT%H%M%SZ")
    backup_root = project_root / ".miku" / "backups" / patch_id
    target = backup_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    manifest = project_root / ".miku" / "backups" / "last.json"
    manifest.write_text(json.dumps({"patch_id": patch_id, "files": [relative_path]}), encoding="utf-8")
    return backup_root
```

- [ ] **Step 4: Implement patch engine and undo manager**

Create `src/mikucode/editing/patch.py`:

```python
from pathlib import Path

from mikucode.config import ensure_miku_dir
from mikucode.editing.backup import create_backup
from mikucode.editing.diff import unified_diff
from mikucode.permissions.policy import PathPolicy
from mikucode.runtime.actions import ToolResult


class PatchEngine:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        ensure_miku_dir(self.project_root)
        self.path_policy = PathPolicy(self.project_root)

    def apply_patches(self, patches: list[dict]) -> ToolResult:
        diffs: list[str] = []
        changed: list[str] = []
        for patch in patches:
            kind = patch.get("kind")
            if kind == "search_replace":
                result = self._apply_search_replace(patch)
            elif kind == "create_file":
                result = self._apply_create_file(patch)
            else:
                return ToolResult(ok=False, tool="apply_patch", summary=f"Unsupported patch kind: {kind}")
            if not result.ok:
                return result
            diffs.append(result.content)
            changed.append(result.metadata["path"])
        return ToolResult(
            ok=True,
            tool="apply_patch",
            summary=f"Applied {len(changed)} patch(es)",
            content="\n".join(diffs),
            metadata={"changed_files": changed},
        )

    def _apply_search_replace(self, patch: dict) -> ToolResult:
        path = str(patch["path"])
        old_text = str(patch["old_text"])
        new_text = str(patch["new_text"])
        resolved = self.path_policy.ensure_inside_project(path)
        before = resolved.read_text(encoding="utf-8")
        count = before.count(old_text)
        if count != 1:
            return ToolResult(ok=False, tool="apply_patch", summary=f"old_text must match exactly once; got {count}", metadata={"path": path})
        after = before.replace(old_text, new_text, 1)
        create_backup(self.project_root, path)
        resolved.write_text(after, encoding="utf-8")
        diff = unified_diff(path, before, after)
        (self.project_root / ".miku" / "patches").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".miku" / "patches" / "last.diff").write_text(diff, encoding="utf-8")
        return ToolResult(ok=True, tool="apply_patch", summary=f"Patched {path}", content=diff, metadata={"path": path})

    def _apply_create_file(self, patch: dict) -> ToolResult:
        path = str(patch["path"])
        content = str(patch["content"])
        resolved = self.path_policy.ensure_inside_project(path)
        if resolved.exists():
            return ToolResult(ok=False, tool="apply_patch", summary=f"File already exists: {path}", metadata={"path": path})
        resolved.parent.mkdir(parents=True, exist_ok=True)
        before = ""
        resolved.write_text(content, encoding="utf-8")
        diff = unified_diff(path, before, content)
        return ToolResult(ok=True, tool="apply_patch", summary=f"Created {path}", content=diff, metadata={"path": path})
```

Create `src/mikucode/editing/undo.py`:

```python
import json
import shutil
from pathlib import Path

from mikucode.runtime.actions import ToolResult


class UndoManager:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def undo_last(self) -> ToolResult:
        manifest_path = self.project_root / ".miku" / "backups" / "last.json"
        if not manifest_path.exists():
            return ToolResult(ok=False, tool="undo", summary="No backup manifest found")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        patch_id = manifest["patch_id"]
        restored: list[str] = []
        for relative_path in manifest["files"]:
            backup = self.project_root / ".miku" / "backups" / patch_id / relative_path
            target = self.project_root / relative_path
            if not backup.exists():
                return ToolResult(ok=False, tool="undo", summary=f"Missing backup: {backup}")
            shutil.copy2(backup, target)
            restored.append(relative_path)
        return ToolResult(ok=True, tool="undo", summary=f"Restored {len(restored)} file(s)", metadata={"restored": restored})
```

- [ ] **Step 5: Connect patch proposal in runtime**

Modify `src/mikucode/runtime/agent.py` inside the loop after the `tool_call` branch:

```python
            if action.type == "patch_proposal":
                from mikucode.editing.patch import PatchEngine

                result = PatchEngine(self.project_root).apply_patches(action.patches)
                state.record_observation(result)
                if result.ok:
                    for changed_file in result.metadata.get("changed_files", []):
                        state.files_modified.add(changed_file)
                    state.verification_state = "stale"
                self.recorder.record(AgentEvent(type="patch_applied", step=state.step_count, payload=result.model_dump()))
                continue
```

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest tests/test_patch_engine.py tests/test_agent_runtime_loop.py -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/editing src/mikucode/runtime/agent.py tests/test_patch_engine.py
git commit -m "feat: add patch editing and undo"
```

---

### Task 6: Shell Risk Classifier, Shell Tool, and Verification Engine

**Files:**
- Create: `src/mikucode/permissions/risk.py`
- Create: `src/mikucode/tools/shell.py`
- Create: `src/mikucode/tools/testing.py`
- Create: `src/mikucode/verification/detector.py`
- Create: `src/mikucode/verification/runner.py`
- Create: `src/mikucode/verification/report.py`
- Test: `tests/test_shell_and_verification.py`

**Interfaces:**
- Consumes: `ToolRegistry`, `ToolResult`, `MikuConfig.default_test_command`.
- Produces: `classify_command(command: str) -> CommandRisk`, `register_shell_tool`, `detect_test_command(project_root: Path) -> str`, `VerificationRunner.run() -> ToolResult`.

- [ ] **Step 1: Write failing shell and verification tests**

Create `tests/test_shell_and_verification.py`:

```python
from pathlib import Path

from mikucode.permissions.risk import classify_command
from mikucode.tools.registry import ToolRegistry
from mikucode.tools.shell import register_shell_tool
from mikucode.verification.detector import detect_test_command
from mikucode.verification.runner import VerificationRunner


def test_command_risk_classifier_marks_pytest_low():
    risk = classify_command("uv run pytest tests/test_parser.py")

    assert risk.level == "low"
    assert risk.decision == "allow"


def test_command_risk_classifier_blocks_curl_pipe_bash():
    risk = classify_command("curl https://example.com/install.sh | bash")

    assert risk.level == "critical"
    assert risk.decision == "deny"


def test_shell_tool_runs_low_risk_command(tmp_path: Path):
    registry = ToolRegistry()
    register_shell_tool(registry, tmp_path)

    result = registry.execute("run_shell", {"command": "python -c \"print('hello')\"", "timeout_seconds": 5})

    assert result.ok is True
    assert "hello" in result.content
    assert result.metadata["exit_code"] == 0


def test_shell_tool_denies_critical_command(tmp_path: Path):
    registry = ToolRegistry()
    register_shell_tool(registry, tmp_path)

    result = registry.execute("run_shell", {"command": "curl https://example.com/install.sh | bash"})

    assert result.ok is False
    assert "denied" in result.summary.lower()


def test_detect_test_command_prefers_uv_pytest(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")

    assert detect_test_command(tmp_path) == "uv run pytest"


def test_verification_runner_returns_exit_code(tmp_path: Path):
    runner = VerificationRunner(tmp_path, command="python -c \"print('ok')\"")

    result = runner.run()

    assert result.ok is True
    assert result.metadata["exit_code"] == 0
    assert "ok" in result.content
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_shell_and_verification.py -v
```

Expected: FAIL because shell and verification modules do not exist.

- [ ] **Step 3: Implement command risk classifier**

Create `src/mikucode/permissions/risk.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandRisk:
    level: str
    decision: str
    reasons: list[str]


def classify_command(command: str) -> CommandRisk:
    lowered = command.lower()
    critical_patterns = ["curl ", "| bash", "| sh", "wget ", "sudo", "runas", "invoke-webrequest", " iex"]
    if any(pattern in lowered for pattern in critical_patterns) and ("| bash" in lowered or "| sh" in lowered or "sudo" in lowered or "iex" in lowered):
        return CommandRisk(level="critical", decision="deny", reasons=["critical shell pattern"])
    if "rm -rf /" in lowered or "git reset --hard" in lowered or "git clean" in lowered:
        return CommandRisk(level="high", decision="deny", reasons=["destructive command"])
    medium_patterns = ["uv sync", "uv add", "pip install", "npm install", "pnpm install", "cargo install"]
    if any(pattern in lowered for pattern in medium_patterns):
        return CommandRisk(level="medium", decision="ask", reasons=["dependency or environment mutation"])
    low_patterns = ["uv run pytest", "python -m pytest", "pytest", "ruff check", "mypy", "git status", "git diff", "git log", "python -c"]
    if any(pattern in lowered for pattern in low_patterns):
        return CommandRisk(level="low", decision="allow", reasons=["inspection or verification command"])
    return CommandRisk(level="medium", decision="ask", reasons=["unclassified command"])
```

- [ ] **Step 4: Implement shell tool and verification runner**

Create `src/mikucode/tools/shell.py`:

```python
import subprocess
from pathlib import Path

from mikucode.permissions.risk import classify_command
from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry


def register_shell_tool(registry: ToolRegistry, project_root: Path) -> None:
    def run_shell(arguments: dict) -> ToolResult:
        command = str(arguments["command"])
        timeout_seconds = int(arguments.get("timeout_seconds", 30))
        risk = classify_command(command)
        if risk.decision == "deny":
            return ToolResult(ok=False, tool="run_shell", summary=f"Command denied: {', '.join(risk.reasons)}", metadata={"risk_level": risk.level})
        if risk.decision == "ask":
            return ToolResult(ok=False, tool="run_shell", summary="Command requires user approval in B-version non-interactive tool path", metadata={"risk_level": risk.level})
        completed = subprocess.run(
            command,
            cwd=project_root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        content = (completed.stdout + completed.stderr)[:20_000]
        return ToolResult(
            ok=completed.returncode == 0,
            tool="run_shell",
            summary=f"Command exited with {completed.returncode}",
            content=content,
            metadata={"command": command, "exit_code": completed.returncode, "risk_level": risk.level},
        )

    registry.register(
        ToolDefinition(name="run_shell", description="Run a low-risk shell command inside the project root.", risk_level="medium", timeout_seconds=30),
        run_shell,
    )
```

Create `src/mikucode/verification/detector.py`:

```python
from pathlib import Path


def detect_test_command(project_root: Path) -> str:
    if (project_root / "pyproject.toml").exists() and (project_root / "uv.lock").exists():
        return "uv run pytest"
    if (project_root / "pyproject.toml").exists():
        return "uv run pytest"
    if (project_root / "pytest.ini").exists() or (project_root / "tests").exists():
        return "python -m pytest"
    return "uv run pytest"
```

Create `src/mikucode/verification/runner.py`:

```python
from pathlib import Path

from mikucode.runtime.actions import ToolResult
from mikucode.tools.registry import ToolRegistry
from mikucode.tools.shell import register_shell_tool
from mikucode.verification.detector import detect_test_command


class VerificationRunner:
    def __init__(self, project_root: Path, command: str | None = None) -> None:
        self.project_root = project_root.resolve()
        self.command = command or detect_test_command(self.project_root)

    def run(self) -> ToolResult:
        registry = ToolRegistry()
        register_shell_tool(registry, self.project_root)
        result = registry.execute("run_shell", {"command": self.command, "timeout_seconds": 120})
        result.tool = "run_tests"
        return result
```

Create `src/mikucode/tools/testing.py`:

```python
from pathlib import Path

from mikucode.runtime.actions import ToolResult
from mikucode.tools.base import ToolDefinition
from mikucode.tools.registry import ToolRegistry
from mikucode.verification.detector import detect_test_command
from mikucode.verification.runner import VerificationRunner


def register_testing_tools(registry: ToolRegistry, project_root: Path) -> None:
    def detect_tests(arguments: dict) -> ToolResult:
        del arguments
        command = detect_test_command(project_root)
        return ToolResult(ok=True, tool="detect_tests", summary=f"Detected test command: {command}", metadata={"command": command})

    def run_tests(arguments: dict) -> ToolResult:
        command = arguments.get("command")
        return VerificationRunner(project_root, command=command).run()

    registry.register(ToolDefinition(name="detect_tests", description="Detect the project test command."), detect_tests)
    registry.register(ToolDefinition(name="run_tests", description="Run the project test command through the shell policy."), run_tests)
```

Create `src/mikucode/verification/report.py`:

```python
from mikucode.runtime.actions import ToolResult


def summarize_verification(result: ToolResult) -> dict:
    return {
        "command": result.metadata.get("command", "unknown"),
        "exit_code": result.metadata.get("exit_code"),
        "summary": result.summary,
        "passed": result.ok,
    }
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_shell_and_verification.py -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/permissions/risk.py src/mikucode/tools/shell.py src/mikucode/tools/testing.py src/mikucode/verification tests/test_shell_and_verification.py
git commit -m "feat: add shell risk and verification"
```

---

### Task 7: Context Builder and Project/Session Memory

**Files:**
- Create: `src/mikucode/context/file_tree.py`
- Create: `src/mikucode/context/builder.py`
- Create: `src/mikucode/memory/store.py`
- Modify: `src/mikucode/runtime/agent.py`
- Test: `tests/test_context_and_memory.py`

**Interfaces:**
- Consumes: `AgentState`, `.miku/project.md` from Task 1.
- Produces: `build_file_tree(project_root: Path) -> str`, `ContextBuilder.build(state: AgentState) -> list[dict]`, `MemoryStore.read_project_memory() -> str`, `MemoryStore.add_project_memory(text: str, source: str) -> None`.

- [ ] **Step 1: Write failing context and memory tests**

Create `tests/test_context_and_memory.py`:

```python
from pathlib import Path

from mikucode.config import ensure_miku_dir
from mikucode.context.builder import ContextBuilder
from mikucode.context.file_tree import build_file_tree
from mikucode.memory.store import MemoryStore
from mikucode.runtime.actions import ToolResult
from mikucode.runtime.state import AgentState


def test_build_file_tree_ignores_generated_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("", encoding="utf-8")

    tree = build_file_tree(tmp_path)

    assert "src/main.py" in tree
    assert ".venv/ignored.py" not in tree


def test_memory_store_reads_and_appends_project_memory(tmp_path: Path):
    ensure_miku_dir(tmp_path)
    store = MemoryStore(tmp_path)

    store.add_project_memory("Use uv run pytest for tests.", source="user")

    memory = store.read_project_memory()
    assert "Use uv run pytest" in memory
    assert "source: user" in memory


def test_context_builder_includes_task_memory_tree_and_recent_observation(tmp_path: Path):
    ensure_miku_dir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "parser.py").write_text("def parse(): pass", encoding="utf-8")
    state = AgentState.new("fix parser")
    state.record_observation(ToolResult(ok=False, tool="run_tests", summary="parser test failed"))

    messages = ContextBuilder(tmp_path).build(state)
    joined = "\n".join(message["content"] for message in messages)

    assert "fix parser" in joined
    assert "src/parser.py" in joined
    assert "parser test failed" in joined
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_context_and_memory.py -v
```

Expected: FAIL because context and memory modules do not exist.

- [ ] **Step 3: Implement file tree and memory store**

Create `src/mikucode/context/file_tree.py`:

```python
from pathlib import Path

_IGNORED_DIRS = {".git", ".miku", ".venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}


def build_file_tree(project_root: Path, max_files: int = 200) -> str:
    files: list[str] = []
    for item in project_root.rglob("*"):
        rel = item.relative_to(project_root)
        if any(part in _IGNORED_DIRS for part in rel.parts):
            continue
        if item.is_file():
            files.append(rel.as_posix())
        if len(files) >= max_files:
            break
    files.sort()
    return "\n".join(files)
```

Create `src/mikucode/memory/store.py`:

```python
from datetime import UTC, datetime
from pathlib import Path

from mikucode.config import ensure_miku_dir


class MemoryStore:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.miku_dir = ensure_miku_dir(self.project_root)
        self.project_md = self.miku_dir / "project.md"

    def read_project_memory(self) -> str:
        return self.project_md.read_text(encoding="utf-8") if self.project_md.exists() else ""

    def add_project_memory(self, text: str, source: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        with self.project_md.open("a", encoding="utf-8") as handle:
            handle.write(f"\n## Memory entry\n- created_at: {timestamp}\n- source: {source}\n- content: {text}\n")
```

- [ ] **Step 4: Implement context builder and integrate runtime**

Create `src/mikucode/context/builder.py`:

```python
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
            {"role": "system", "content": "You are MikuCode. Return exactly one JSON AgentAction."},
            {"role": "user", "content": state.task},
            {"role": "system", "content": serialized},
        ]
```

Modify `src/mikucode/runtime/agent.py`:

```python
from mikucode.context.builder import ContextBuilder
```

Replace `_build_messages` body with:

```python
    def _build_messages(self, state: AgentState) -> list[dict]:
        return ContextBuilder(self.project_root).build(state)
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_context_and_memory.py tests/test_agent_runtime_loop.py -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/context src/mikucode/memory src/mikucode/runtime/agent.py tests/test_context_and_memory.py
git commit -m "feat: add context builder and memory"
```

---

### Task 8: OpenAI-Compatible Provider, REPL Runtime Wiring, One-Shot Mode, and Undo/Diff Commands

**Files:**
- Create: `src/mikucode/models/openai_compatible.py`
- Modify: `src/mikucode/cli/main.py`
- Modify: `src/mikucode/cli/repl.py`
- Modify: `src/mikucode/tools/registry.py`
- Test: `tests/test_cli_runtime_wiring.py`

**Interfaces:**
- Consumes: `AgentRuntime`, `ToolRegistry`, filesystem/search/testing/shell tools, `UndoManager`.
- Produces: live CLI commands `miku chat`, `miku "task"`, `miku undo`, `miku trace show`.

- [ ] **Step 1: Write failing CLI runtime tests**

Create `tests/test_cli_runtime_wiring.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from mikucode.cli.main import app


def test_one_shot_mock_runtime_reads_file(tmp_path: Path, monkeypatch):
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setenv(
        "MIKU_MOCK_RESPONSES",
        '[{"type":"tool_call","tool":"read_file","arguments":{"path":"hello.txt"},"reason":"Read"},{"type":"final_answer","summary":"done"}]',
    )
    runner = CliRunner()

    result = runner.invoke(app, ["--project-root", str(tmp_path), "read hello"])

    assert result.exit_code == 0
    assert "done" in result.stdout
    assert list((tmp_path / ".miku" / "sessions").glob("*.jsonl"))


def test_undo_command_reports_no_backup(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(app, ["undo", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "No backup" in result.stdout
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_cli_runtime_wiring.py -v
```

Expected: FAIL because CLI runtime wiring is not complete.

- [ ] **Step 3: Implement OpenAI-compatible provider**

Create `src/mikucode/models/openai_compatible.py`:

```python
import os

import httpx

from mikucode.models.base import ModelResponse


class OpenAICompatibleProvider:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("MIKU_OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("MIKU_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("MIKU_MODEL") or "gpt-4o-mini"

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> ModelResponse:
        del tools
        if not self.api_key:
            raise RuntimeError("Missing API key. Set MIKU_OPENAI_API_KEY or OPENAI_API_KEY.")
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages, "temperature": 0},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return ModelResponse(content=data["choices"][0]["message"]["content"])
```

- [ ] **Step 4: Wire CLI to runtime with mock fallback for tests**

Modify `src/mikucode/cli/main.py` to include these imports:

```python
import json
import os

from mikucode.editing.undo import UndoManager
from mikucode.models.mock import MockProvider
from mikucode.models.openai_compatible import OpenAICompatibleProvider
from mikucode.runtime.agent import AgentRuntime
from mikucode.tools.filesystem import register_filesystem_tools
from mikucode.tools.registry import ToolRegistry
from mikucode.tools.search import register_search_tools
from mikucode.tools.shell import register_shell_tool
from mikucode.tools.testing import register_testing_tools
```

Add helper functions:

```python
def build_registry(project_root: Path) -> ToolRegistry:
    registry = ToolRegistry()
    register_filesystem_tools(registry, project_root)
    register_search_tools(registry, project_root)
    register_shell_tool(registry, project_root)
    register_testing_tools(registry, project_root)
    return registry


def build_provider():
    mock = os.getenv("MIKU_MOCK_RESPONSES")
    if mock:
        encoded = json.loads(mock)
        responses = [json.dumps(item) if isinstance(item, dict) else str(item) for item in encoded]
        return MockProvider(responses=responses)
    return OpenAICompatibleProvider()
```

Update the one-shot branch inside `main`:

```python
    ensure_miku_dir(project_root)
    runtime = AgentRuntime(
        project_root=project_root,
        provider=build_provider(),
        registry=build_registry(project_root),
    )
    state = runtime.run(task)
    if state.done:
        console.print("[green]Done.[/green]")
    for observation in state.observations[-3:]:
        console.print(observation.summary)
```

Add an `undo` command:

```python
@app.command()
def undo(project_root: Path = typer.Option(Path.cwd(), help="Project root")) -> None:
    ensure_miku_dir(project_root)
    result = UndoManager(project_root).undo_last()
    console.print(result.summary)
```

- [ ] **Step 5: Update REPL to call runtime for user tasks**

Modify `src/mikucode/cli/repl.py` imports:

```python
from mikucode.cli.main import build_provider, build_registry
from mikucode.editing.undo import UndoManager
from mikucode.runtime.agent import AgentRuntime
```

Replace non-command handling in `MikuRepl.run` with:

```python
            if user_input == "/undo":
                result = UndoManager(self.config.project_root).undo_last()
                self.console.print(result.summary)
                continue
            runtime = AgentRuntime(
                project_root=self.config.project_root,
                provider=build_provider(),
                registry=build_registry(self.config.project_root),
            )
            state = runtime.run(user_input)
            self.console.print("[green]Done.[/green]" if state.done else "[yellow]Stopped.[/yellow]")
            for observation in state.observations[-3:]:
                self.console.print(observation.summary)
```

If this creates a circular import, move `build_registry` and `build_provider` to a new file `src/mikucode/cli/factory.py` and import them from both `main.py` and `repl.py`.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest tests/test_cli_runtime_wiring.py -v
uv run pytest -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/models/openai_compatible.py src/mikucode/cli tests/test_cli_runtime_wiring.py
git commit -m "feat: wire cli to mikucode runtime"
```

---

### Task 9: Trace Replay, Smoke Benchmark, README, and B-Version Acceptance Demo

**Files:**
- Create: `src/mikucode/tracing/replay.py`
- Create: `src/mikucode/benchmark/smoke.py`
- Modify: `src/mikucode/cli/main.py`
- Modify: `README.md`
- Create: `benchmarks/smoke/parser_bug/task.md`
- Create: `benchmarks/smoke/parser_bug/repo/pyproject.toml`
- Create: `benchmarks/smoke/parser_bug/repo/src/parser_demo.py`
- Create: `benchmarks/smoke/parser_bug/repo/tests/test_parser_demo.py`
- Test: `tests/test_trace_replay_and_benchmark.py`

**Interfaces:**
- Consumes: JSONL trace files, CLI factory/runtime, mock responses.
- Produces: `render_trace(path: Path) -> str`, `run_smoke_benchmark(project_root: Path) -> dict`.

- [ ] **Step 1: Write failing trace replay and benchmark tests**

Create `tests/test_trace_replay_and_benchmark.py`:

```python
import json
from pathlib import Path

from mikucode.benchmark.smoke import run_smoke_benchmark
from mikucode.tracing.replay import render_trace


def test_render_trace_summarizes_events(tmp_path: Path):
    trace = tmp_path / "session.jsonl"
    trace.write_text(
        "\n".join(
            [
                json.dumps({"type": "user_task", "payload": {"task": "fix tests"}}),
                json.dumps({"type": "tool_result", "payload": {"tool": "run_tests", "summary": "failed"}}),
                json.dumps({"type": "final_report", "payload": {"summary": "done"}}),
            ]
        ),
        encoding="utf-8",
    )

    rendered = render_trace(trace)

    assert "user_task" in rendered
    assert "run_tests" in rendered
    assert "done" in rendered


def test_smoke_benchmark_returns_metrics(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MIKU_MOCK_RESPONSES", '[{"type":"final_answer","summary":"done"}]')

    result = run_smoke_benchmark(tmp_path)

    assert result["tasks"] >= 1
    assert "passed" in result
    assert "duration_seconds" in result
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run pytest tests/test_trace_replay_and_benchmark.py -v
```

Expected: FAIL because trace replay and benchmark modules do not exist.

- [ ] **Step 3: Implement trace replay**

Create `src/mikucode/tracing/replay.py`:

```python
import json
from pathlib import Path


def render_trace(path: Path) -> str:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        event = json.loads(raw)
        event_type = event.get("type", "unknown")
        payload = event.get("payload", {})
        summary = payload.get("summary") or payload.get("task") or payload.get("tool") or ""
        lines.append(f"{event_type}: {summary}")
    return "\n".join(lines)
```

- [ ] **Step 4: Implement smoke benchmark harness**

Create `src/mikucode/benchmark/smoke.py`:

```python
import time
from pathlib import Path

from mikucode.cli.main import build_provider, build_registry
from mikucode.runtime.agent import AgentRuntime


def run_smoke_benchmark(project_root: Path) -> dict:
    started = time.perf_counter()
    task_root = project_root / "bench-smoke-repo"
    task_root.mkdir(parents=True, exist_ok=True)
    (task_root / "hello.txt").write_text("hello", encoding="utf-8")
    runtime = AgentRuntime(project_root=task_root, provider=build_provider(), registry=build_registry(task_root), max_steps=5)
    state = runtime.run("Read hello.txt and finish.")
    duration = time.perf_counter() - started
    return {
        "tasks": 1,
        "passed": 1 if state.done else 0,
        "failed": 0 if state.done else 1,
        "steps": state.step_count,
        "duration_seconds": round(duration, 3),
    }
```

- [ ] **Step 5: Add CLI commands for trace and benchmark**

Modify `src/mikucode/cli/main.py` imports:

```python
from mikucode.benchmark.smoke import run_smoke_benchmark
from mikucode.tracing.replay import render_trace
```

Add commands:

```python
trace_app = typer.Typer(help="Trace replay commands")
bench_app = typer.Typer(help="Benchmark commands")
app.add_typer(trace_app, name="trace")
app.add_typer(bench_app, name="bench")


@trace_app.command("show")
def trace_show(path: Path) -> None:
    console.print(render_trace(path))


@bench_app.command("smoke")
def bench_smoke(project_root: Path = typer.Option(Path.cwd(), help="Project root")) -> None:
    result = run_smoke_benchmark(project_root)
    console.print(result)
```

- [ ] **Step 6: Add benchmark fixture files**

Create `benchmarks/smoke/parser_bug/task.md`:

```markdown
Fix the parser so it strips surrounding whitespace before returning the parsed value.
```

Create `benchmarks/smoke/parser_bug/repo/pyproject.toml`:

```toml
[project]
name = "parser-bug"
version = "0.1.0"
requires-python = ">=3.11"

[dependency-groups]
dev = ["pytest>=8.2.0"]
```

Create `benchmarks/smoke/parser_bug/repo/src/parser_demo.py`:

```python
def parse_value(text: str) -> str:
    return text
```

Create `benchmarks/smoke/parser_bug/repo/tests/test_parser_demo.py`:

```python
from parser_demo import parse_value


def test_parse_value_strips_whitespace():
    assert parse_value("  miku  ") == "miku"
```

- [ ] **Step 7: Write README**

Replace `README.md` with:

```markdown
# MikuCode

MikuCode is a Python-based local coding agent runtime inspired by Claude Code/Codex.
It treats the LLM as a decision engine, not an executor: the model emits structured JSON actions, while the runtime validates actions, enforces permissions, executes tools, applies patches, records traces, and verifies results.

## Highlights

- OpenAI-compatible model layer.
- JSON action protocol.
- REPL-first CLI plus one-shot command mode.
- Permissioned filesystem, search, shell, and testing tools.
- Patch-based editing with diff generation, backups, and undo.
- Context builder and project/session memory.
- Evidence-driven verification using commands such as `uv run pytest`.
- Replayable JSONL traces.
- Smoke benchmark harness.

## Quickstart

```bash
uv sync
uv run miku init
uv run miku chat
```

For tests:

```bash
uv run pytest
uv run ruff check src tests
```

## Model Configuration

MikuCode uses OpenAI-compatible chat completions.

```bash
export MIKU_OPENAI_BASE_URL="https://api.openai.com/v1"
export MIKU_OPENAI_API_KEY="..."
export MIKU_MODEL="gpt-4o-mini"
```

For deterministic local tests, set `MIKU_MOCK_RESPONSES` to a JSON array of action objects.

## Safety Model

The B version implements developer-safety guardrails, not a hardened adversarial sandbox.
It includes project-root path checks, secret-file denial, command risk classification, timeouts, trace redaction, patch backups, and undo.

## Roadmap

The C flagship roadmap includes Web trace dashboard, MCP-like external plugins, role-based agents, Docker sandbox, advanced verification planning, benchmark reports, and IDE integration prototype.
```

- [ ] **Step 8: Run full verification and commit**

Run:

```bash
uv run pytest -v
uv run ruff check src tests
```

Expected: PASS.

Commit:

```bash
git add src/mikucode/tracing/replay.py src/mikucode/benchmark src/mikucode/cli/main.py README.md benchmarks tests/test_trace_replay_and_benchmark.py
git commit -m "feat: add trace replay benchmark and docs"
```

---

## Final B-Version Verification Checklist

Run these commands after Task 9:

```bash
uv run pytest -v
uv run ruff check src tests
uv run miku --help
uv run miku init
uv run miku bench smoke
```

Expected outcomes:

```text
pytest passes
ruff passes
miku --help displays CLI commands
miku init creates .miku/
miku bench smoke reports one smoke task result
```

Manual demo verification:

```bash
$env:MIKU_MOCK_RESPONSES='[{"type":"tool_call","tool":"read_file","arguments":{"path":"hello.txt"},"reason":"Read"},{"type":"final_answer","summary":"done"}]'
uv run miku "read hello"
```

Expected:

```text
Done.
Read hello.txt
```

## Plan Self-Review

Spec coverage:

- Project skeleton and `uv` workflow: Task 1.
- Runtime state, action schema, trace: Task 2.
- Filesystem/search tools and path sandbox: Task 3.
- Agent loop and JSON command mode: Task 4.
- Patch proposal, diff, backup, undo: Task 5.
- Shell risk, verification, `uv run pytest`: Task 6.
- Context and memory: Task 7.
- OpenAI-compatible provider, REPL, one-shot CLI: Task 8.
- Trace replay, benchmark, README/demo: Task 9.
- C-version roadmap remains documented and excluded from B-version implementation: Global Constraints and README.

Placeholder scan:

- The plan contains no placeholder markers or unspecified implementation steps.
- Every task includes file paths, test commands, expected outcomes, implementation snippets, and commit commands.

Type consistency:

- `AgentAction`, `ToolResult`, `AgentState`, `ToolRegistry`, `TraceRecorder`, `PathPolicy`, `PatchEngine`, `UndoManager`, `VerificationRunner`, `ContextBuilder`, and `MemoryStore` are named consistently across tasks.
- `miku` is the CLI command and `mikucode` is the Python package name throughout the plan.
