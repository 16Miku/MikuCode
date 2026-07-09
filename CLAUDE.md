# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MikuCode is a Python-based local coding agent runtime inspired by Claude Code/Codex. It treats the LLM as a decision engine, not an executor: the model emits structured `AgentAction` objects, and the runtime validates, authorizes, executes, records, rolls back, and verifies. The LLM never directly edits files or runs shell commands.

Current state: only Task 1 (project skeleton + CLI + `.miku` init) is implemented. Tasks 2–9 (runtime, models, tools, permissions, editing, context, memory, tracing, verification, benchmark) are planned but not started.

## Commands

```bash
uv sync                                    # install/sync all dependencies
uv run pytest                              # run all tests
uv run pytest tests/test_cli_init.py -v    # run a single test file
uv run pytest tests/test_cli_init.py::test_init_creates_miku_project_files -v  # single test
uv run ruff check src tests                # lint
uv run miku --help                         # CLI help
uv run miku init --project-root <path>     # initialize .miku/ in a project
uv run miku chat --project-root <path>     # start interactive REPL
```

All Python dependency management, test execution, and CLI invocation must use `uv`.

## Architecture

**Core principle:** The model proposes structured intent; the runtime gates execution. File edits must flow through patch proposal → diff preview → backup → apply → undo. Shell commands must flow through risk classification → permission policy → timeout-bounded execution. Final reports must be assembled from runtime evidence (exit codes, test output, changed files), not model claims.

**Module boundaries** (planned, from design spec):

- `cli/` — user interaction only, never contains agent decision logic
- `runtime/` — agent loop, state machine, action parsing
- `models/` — provider-agnostic model interface; OpenAI-compatible first, JSON command mode default
- `tools/` — schema-validated tool implementations registered via `ToolRegistry`
- `permissions/` — path sandbox + command risk classification + permission policy
- `editing/` — patch validation, diff generation, backup, undo (never direct `write_file`)
- `context/` — bounded prompt/context assembly with token budget
- `memory/` — project memory (`.miku/project.md`) and session memory
- `tracing/` — JSONL event recording and replay
- `verification/` — test command detection, execution, evidence-based reports
- `benchmark/` — smoke benchmark harness

**Key interfaces** (already implemented in Task 1):

- `MikuConfig(project_root, miku_dir, permission_mode="auto-safe", default_test_command="uv run pytest")`
- `ensure_miku_dir(project_root: Path) -> Path` — idempotent, creates `.miku/` with `sessions/`, `patches/`, `backups/`, seeds `project.md` and `config.toml` only if missing
- `load_config(project_root: Path) -> MikuConfig`
- Typer `app` at `mikucode.cli.main:app`

## CLI Architecture Note

The CLI uses a **single Typer command** with `args: List[str]` + `--project-root` option, then manually dispatches on `args[0]` (`init` / `chat` / one-shot task). This differs from the plan's original multi-command Typer group approach, which caused `--project-root` to be parsed as a subcommand name. Do not revert to `@app.command()` subcommands with a root positional `task` argument — Typer's group resolution conflicts with free-form one-shot task text.

## Design and Plan Documents

- `docs/superpowers/specs/2026-07-07-mikucode-design.md` — full design spec (architecture, modules, protocols, safety model, B/C version boundaries)
- `docs/superpowers/plans/2026-07-07-mikucode-implementation.md` — 9-task TDD implementation plan with exact file paths, test code, and commit points
- `docs/superpowers/goals/2026-07-09-task-1-goal.md` — Task 1 executable goal with TDD steps, acceptance criteria, and known pitfalls

When the plan's code examples conflict with this repo's actual implementation, trust the **test contracts and interface signatures** over the plan's implementation snippets. The plan is the SSOT for what to build next; the repo is the SSOT for what actually exists.

## B-Version Constraints

- Python `>=3.11`, all commands through `uv`
- Model layer: OpenAI-compatible first, JSON command mode default
- REPL is primary interaction mode; one-shot CLI is secondary
- Do not implement: Web dashboard, full MCP protocol, Docker sandbox, IDE extension, autonomous parallel multi-agent
- `.miku/` directory is gitignored runtime state — never commit it
- `pydantic` and `httpx` are declared as dependencies but not yet imported; they are reserved for models/runtime in later tasks

## Working Principles

### 第一性原理 (First Principles)

分析任何问题时，必须回归事物的本质和基本真理，而不是依赖类比或既有做法。

- **质疑一切**：对现有方案、传统做法和假设进行深度质疑，追溯其最根本的前提。
- **解构与重构**：将复杂问题拆解为最基本的组成部分，然后从零开始重新构建解决方案。
- **追求本质**：关注问题的核心，忽略干扰信息，确保每一项技术决策都基于最基础、最不可再分的真实需求。

### 对抗式审查 (Adversarial Review)

在执行任务和生成内容时，必须扮演"魔鬼辩护人"的角色，主动寻找自身方案、代码、逻辑中的缺陷、漏洞和潜在风险。

- **主动质疑**：在完成任何步骤后，都必须自问"这可能在哪里失败？""是否存在逻辑漏洞？"不要全盘或盲目接受。
- **压力测试**：对代码健壮性、数据可靠性、异常处理、边界条件进行严格的压力测试和逻辑推演。
- **寻求最优**：通过对抗性思维，不断挑战现有方案，直到找到最 robust、最高效、最优雅的解决方案。

### Git 提交规范

- 提交信息使用**中文**，详细描述变更内容和原因。
- 格式示例：`feat: 初始化 mikucode CLI 骨架，包含 init/chat/one-shot 三种入口`

## Known Deviations From Plan

1. **CLI architecture**: single Typer command with manual dispatch instead of multi-command Typer group (Typer group resolution conflicts with free-form one-shot task text)
2. **Extra tests**: `test_init_is_idempotent_and_does_not_overwrite_existing_files` and `test_one_shot_task_prints_placeholder_and_initializes_project` were added beyond plan's 2-test specification
3. **`src/mikucode/cli/__init__.py`**: not listed in plan's File Structure Map but required as package marker
4. **hatchling build backend**: added to `pyproject.toml` so `uv run miku` works as entrypoint
