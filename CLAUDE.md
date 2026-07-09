# CLAUDE.md

本文件为在本仓库中工作的 AI 编程助手（如 Claude Code / 同类 Agent）提供指引。

## 项目概览

MikuCode 是 Python 本地编程智能体运行时，思路类似 Claude Code / Codex：把 LLM 当作**决策引擎**，不是执行器。模型输出结构化 `AgentAction`，运行时负责校验、授权、执行、记录、回滚与基于证据的验证。模型不直接改文件或裸跑 shell。

**当前状态：B 版 Task 1–9 已实现并通过测试**（CLI、runtime、工具、补丁、验证、上下文、OpenAI 兼容 Provider、trace 回放、smoke 等）。

## 常用命令

```bash
uv sync                                    # 安装/同步依赖
uv run pytest                              # 全部测试
uv run pytest tests/test_cli_init.py -v    # 单文件
uv run ruff check src tests                # 静态检查
uv run miku --help                         # CLI 帮助
uv run miku init --project-root <path>     # 初始化 .miku/
uv run miku chat --project-root <path>     # 交互 REPL
```

Python 依赖安装、运行、测试、CLI 调用**一律使用 `uv`**。

## 架构原则

- **模型提议，运行时门控**：文件编辑必须走 patch proposal →（diff）→ backup → apply → undo。
- **Shell** 必须走风险分级 → 策略 → 超时执行。
- **最终结论**应基于运行时证据（exit code、测试输出、变更文件、trace），而非模型口头声明。

### 模块边界

- `cli/` — 仅用户交互；不写 agent 决策逻辑
- `runtime/` — 循环、状态、动作解析（含模型输出容错）
- `models/` — 与供应商无关的接口；OpenAI 兼容优先
- `tools/` — 经 `ToolRegistry` 注册的 schema 化工具
- `permissions/` — 路径沙箱 + 命令风险
- `editing/` — 补丁校验、diff、备份、undo（默认不暴露直接 write_file）
- `context/` — 有预算的上下文组装
- `memory/` — 项目记忆（`.miku/project.md`）
- `tracing/` — JSONL 事件与回放
- `verification/` — 测试检测与执行
- `benchmark/` — 冒烟基准

### 关键接口（摘要）

- `MikuConfig` / `ensure_miku_dir` / `load_config` / `load_env_files`
- `AgentRuntime.run(task)`、`AgentAction` / `ToolResult` / `AgentState`
- `build_provider()` / `build_registry(project_root)`（`cli/factory.py`）
- `PatchEngine.apply_patches` / `UndoManager.undo_last`
- `TraceRecorder` / `render_trace` / `run_smoke_benchmark`

## CLI 架构说明

使用**单一 Typer 命令** + `args` 手动分发（`init` / `chat` / `undo` / `trace show` / `bench smoke` / one-shot 任务）。不要改回会与 free-form one-shot 冲突的多 subcommand group。

配置：进程环境变量或项目 `.env`（`load_env_files`，不覆盖已有 env）。

## 设计与计划文档

- `docs/superpowers/specs/2026-07-07-mikucode-design.md` — 设计规格
- `docs/superpowers/plans/2026-07-07-mikucode-implementation.md` — 9 Task 实现计划
- `docs/superpowers/goals/` — 各 Task 可执行 goal

计划代码片段与仓库冲突时：**以测试契约与当前仓库实现为准**。

## B 版约束

- Python `>=3.11`，命令走 `uv`
- 模型层：OpenAI 兼容优先，JSON 指令模式
- REPL 为主，one-shot 为辅
- 不实现：Web 控制台、完整 MCP、Docker 沙箱、IDE 扩展、自治并行多 Agent
- `.miku/` 为运行时状态，已 gitignore，勿提交
- 密钥用 `.env`（gitignore），只提交 `.env.example`

## 工作原则


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

### Git 提交

- 提交信息使用**中文**，说明变更与原因
- 示例：`fix: search_text 参数容错与工具执行 fail-soft`

## 已知与计划的偏差（节选）

1. CLI 为单命令手动 dispatch，而非多 command group
2. `build_provider` / `build_registry` 在 `cli/factory.py`
3. 运行时对模型输出有容错（纯文本、扁平 patch、搜索别名等）
4. 工具执行 fail-soft，异常转为 `ToolResult(ok=False)` 而非打崩 REPL
