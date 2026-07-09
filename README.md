# MikuCode

MikuCode is a Python-based local coding agent runtime inspired by Claude Code/Codex.

It treats the LLM as a **decision engine**, not an executor: the model emits structured JSON `AgentAction` objects, while the runtime validates them, enforces permissions, executes tools, applies patches, records traces, and verifies results with evidence.

## Highlights

- **OpenAI-compatible model layer** (httpx) with MockProvider for deterministic tests
- **JSON action protocol** (`tool_call`, `patch_proposal`, `final_answer`, …)
- **REPL + one-shot CLI** (`miku chat`, `miku "<task>"`)
- **Permissioned tools** — path sandbox, secret-file denial, shell risk classification
- **Patch-based editing** — unique `search_replace`, `create_file`, backup, undo
- **Context + project memory** — file tree, `.miku/project.md`, recent observations
- **Evidence-driven verification** — test command detection and gated shell runs
- **Replayable traces** — JSONL sessions with secret redaction (`miku trace show`)
- **Smoke benchmark** — deterministic end-to-end harness (`miku bench smoke`)

## Quickstart

Requires Python `>=3.11` and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run miku init
uv run miku chat
```

One-shot task:

```bash
uv run miku "list project files and summarize structure"
```

Undo last patch:

```bash
uv run miku undo
```

Replay a session trace:

```bash
uv run miku trace show .miku/sessions/<timestamp>-session.jsonl
```

Run the smoke benchmark (uses a built-in mock when no API key is set):

```bash
uv run miku bench smoke
```

Tests and lint:

```bash
uv run pytest
uv run ruff check src tests
```

## Model Configuration

| Environment variable | Purpose |
|----------------------|---------|
| `MIKU_OPENAI_BASE_URL` | OpenAI-compatible API base (default `https://api.openai.com/v1`) |
| `MIKU_OPENAI_API_KEY` | API key (also accepts `OPENAI_API_KEY`) |
| `MIKU_MODEL` | Model name (default `gpt-4o-mini`) |
| `MIKU_MOCK_RESPONSES` | JSON array of scripted AgentAction objects for offline/mock runs |

Example mock one-shot (PowerShell):

```powershell
$env:MIKU_MOCK_RESPONSES = '[{"type":"final_answer","summary":"done"}]'
uv run miku "say hello"
```

## Safety Model (B version)

MikuCode B is a **developer-safety** runtime, not a hardened adversarial sandbox:

- **Path sandbox** — tools resolve paths under project root; reject escapes, secrets (`.env`, keys), and `.git` internals
- **Command risk** — `classify_command` → allow / ask / deny; only low-risk shell commands auto-run
- **Timeouts & output limits** — shell runs are time-bounded; large outputs are truncated
- **Trace redaction** — secrets (API keys, Bearer tokens) are redacted before JSONL write
- **Patch backups & undo** — edits go through patch proposal → backup → apply; `miku undo` restores last backup

Out of B-version scope: Docker sandbox, full MCP, Web dashboard, IDE extension, multi-agent parallelism.

## Project layout

```text
src/mikucode/
  cli/           # Typer entry, REPL, provider/registry factory
  runtime/       # Agent loop, actions, state, events
  models/        # Mock + OpenAI-compatible providers
  tools/         # filesystem, search, shell, testing
  permissions/   # path policy + command risk
  editing/       # patch, diff, backup, undo
  context/       # file tree + context builder
  memory/        # project.md memory store
  tracing/       # JSONL recorder + replay
  verification/  # test detection + runner
  benchmark/     # smoke harness
```

Runtime state lives in `.miku/` (gitignored): sessions, patches, backups, config, project memory.

## Roadmap (C version)

- Web dashboard for traces and sessions
- Full MCP protocol support
- Role-based / multi-agent workflows
- Docker / stronger sandbox isolation
- Advanced verification suites and HTML/JSON benchmark reports
- IDE extension integration

## License

See repository root for license terms if present; otherwise treat as private/study project unless published otherwise.
