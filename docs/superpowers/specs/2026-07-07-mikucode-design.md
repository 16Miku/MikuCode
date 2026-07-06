# MikuCode Design

Date: 2026-07-07  
Status: Approved design draft, ready for user review  
Scope: 4–6 week resume-grade version, with an 8–10 week flagship roadmap

## 1. Project Goal

MikuCode is a Python-based local coding agent runtime inspired by Claude Code and Codex. Its goal is not to clone every product feature, but to reproduce the core engineering mechanisms that make a coding agent trustworthy on a local repository.

The B version will deliver a usable CLI and REPL tool that can:

- Understand a user coding task.
- Build relevant project context.
- Ask an OpenAI-compatible model for structured actions.
- Execute tools through a controlled runtime.
- Search, read, and inspect local code.
- Propose code changes as patches, not direct writes.
- Show diffs before applying changes.
- Back up modified files and support undo.
- Run tests through a permissioned shell tool.
- Produce final reports grounded in real verification evidence.
- Save replayable JSONL session traces.
- Run a small smoke benchmark suite.

The intended resume positioning is:

> MikuCode — Local Coding Agent Runtime. A Python CLI agent runtime inspired by Claude Code/Codex, featuring an OpenAI-compatible model layer, structured JSON action protocol, permissioned shell execution, patch-based editing, verification workflow, project/session memory, and replayable traces.

## 2. Non-goals

The B version intentionally does not include:

- Full IDE extension.
- Full MCP protocol implementation.
- Web dashboard.
- True hardened security sandbox.
- Docker-based command isolation.
- Parallel autonomous multi-agent execution.
- Whole-repository embedding RAG.
- Cloud collaboration.
- Automatic Git push or PR creation.

These are explicitly reserved for the flagship roadmap.

## 3. Target Users and Resume Positioning

The primary target user is a developer who wants a local coding assistant that can safely inspect a repository, propose small changes, run verification commands, and explain what happened.

The primary resume target is a hybrid of:

- AI Agent / LLM application engineering.
- Developer tooling / infrastructure engineering.

The project should demonstrate the following engineering capabilities:

- Designing an agent runtime rather than a prompt wrapper.
- Separating model intent from real-world side effects.
- Implementing structured tool calling.
- Controlling shell and filesystem risk.
- Designing patch-based editing with rollback.
- Building context selection and memory.
- Recording traces for observability and benchmarking.
- Producing verification-grounded final reports.

## 4. Architecture Overview

MikuCode uses a runtime-first layered architecture:

```text
CLI / REPL
  ↓
AgentRuntime
  ↓
ContextBuilder
  ↓
ModelProvider
  ↓
ActionParser + ActionValidator
  ↓
PermissionPolicy
  ↓
ToolRegistry / PatchEngine / VerificationEngine
  ↓
MemoryStore + TraceRecorder
```

The key architectural principle is:

> The model proposes structured intent. The runtime validates, authorizes, executes, records, rolls back, and verifies.

This means the LLM never directly edits files or executes shell commands. It emits `AgentAction` objects, and the runtime decides whether those actions are valid and safe.

MikuCode exposes two user entry points:

```bash
miku chat
miku "fix failing parser tests"
```

Both entry points call the same `AgentRuntime`. The REPL is the primary experience; one-shot command mode is kept for automation and demos.

## 5. Repository and Package Structure

Recommended layout:

```text
mikucode/
  pyproject.toml
  README.md
  docs/
    architecture.md
    roadmap-flagship.md
    demos/
  examples/
    buggy-python-project/
  benchmarks/
    smoke/
  tests/

  src/
    mikucode/
      cli/
        main.py
        repl.py
        commands.py

      runtime/
        agent.py
        state.py
        actions.py
        events.py

      models/
        base.py
        openai_compatible.py
        mock.py

      context/
        builder.py
        file_tree.py
        ranker.py
        budget.py
        summarizer.py

      tools/
        base.py
        registry.py
        filesystem.py
        search.py
        shell.py
        git.py
        testing.py

      editing/
        patch.py
        diff.py
        backup.py
        undo.py

      permissions/
        policy.py
        risk.py
        prompts.py

      memory/
        project.py
        session.py
        store.py

      verification/
        detector.py
        runner.py
        report.py

      tracing/
        recorder.py
        replay.py

      ui/
        console.py
        panels.py
        trace_view.py

      plugins/
        base.py
        python.py
```

The package should use Python `>=3.11`, managed by `uv`. Suggested dependencies:

- `typer` for CLI commands.
- `rich` for terminal UI.
- `pydantic` for schemas.
- `httpx` for model API calls.
- `pytest` for tests.
- `ruff` for linting.

## 6. Core Modules

### 6.1 `cli/`

The CLI layer handles user interaction only. It must not contain agent decision logic.

Primary commands:

```bash
miku init
miku chat
miku "fix failing tests"
miku diff
miku undo
miku verify
miku memory show
miku trace show <session.jsonl>
miku bench smoke
```

REPL slash commands:

```text
/plan
/status
/diff
/undo
/verify
/tools
/memory
/trace
/exit
```

### 6.2 `runtime/`

The runtime is the core state machine. It maintains:

- Current task.
- Step count.
- Conversation and observation history.
- Current plan.
- Files read.
- Files modified.
- Patch history.
- Verification state.
- Permission decisions.

Recommended runtime states:

```text
IDLE
RECEIVING_TASK
BUILDING_CONTEXT
CALLING_MODEL
PARSING_ACTION
VALIDATING_ACTION
WAITING_PERMISSION
EXECUTING_TOOL
APPLYING_PATCH
VERIFYING
SUMMARIZING
DONE
ERROR
CANCELLED
```

Every transition should emit an `AgentEvent` and be recorded in the JSONL trace.

### 6.3 `models/`

MikuCode is OpenAI-compatible first. The design should still remain provider-agnostic.

Provider interface:

```text
ModelProvider.complete(messages, tools=None, stream=False) -> ModelResponse
```

B version implementations:

- `OpenAICompatibleProvider`.
- `MockProvider` for deterministic tests.

The default action format is JSON command mode. Native OpenAI tool calling is reserved as an experimental or C-version feature.

### 6.4 `tools/`

Tools are registered through `ToolRegistry`. A tool definition includes:

```text
name
description
input_schema
risk_level
permission requirement
timeout_seconds
output_limit_chars
executor
```

B version tools:

```text
list_files
read_file
search_text
run_shell
git_status
git_diff
detect_tests
run_tests
```

Patch application is not exposed as a normal raw write tool. It flows through `patch_proposal` and `PatchEngine`.

### 6.5 `editing/`

The editing module owns patch validation, diff generation, backup, application, and undo.

B version patch kinds:

```text
search_replace
create_file
```

The default editing path must not be direct `write_file`.

### 6.6 `permissions/`

The permission module decides whether an action is allowed, denied, or requires user confirmation.

Inputs:

- Action type.
- Tool definition.
- Tool arguments.
- Command risk result.
- Path sandbox result.
- Permission mode.
- Session allowlist or denylist.

Outputs:

```text
allow
deny
ask_user
```

### 6.7 `context/`

The context module selects what the model needs for the next step.

It should prefer transparent, debuggable signals over early embedding RAG:

- User-mentioned paths and symbols.
- Test failure file paths.
- Search hits.
- Import/module name matches.
- Recently read or edited files.
- Current git diff.

### 6.8 `memory/`

B version memory includes:

- Project memory.
- Session memory.

It does not include global cross-project user memory.

Project memory files live in `.miku/`:

```text
.miku/project.md
.miku/config.toml
.miku/memory.json
```

Session state and traces live in:

```text
.miku/sessions/
.miku/patches/
.miku/backups/
```

### 6.9 `verification/`

The verification module detects project test commands, runs verification commands through the permissioned shell, summarizes evidence, and updates verification state.

For Python projects, MikuCode should prefer `uv`:

```text
uv run pytest
```

### 6.10 `tracing/`

Tracing records every meaningful runtime event as JSONL. It is the basis for debugging, replay, benchmark analysis, and the future Web dashboard.

## 7. Agent Loop

The agent loop is a controlled execution loop:

```text
1. Receive user task.
2. Initialize or update AgentState.
3. Build context.
4. Call the model provider.
5. Parse model output into AgentAction.
6. Validate the action.
7. Check permissions.
8. Execute tool, patch, or verification action.
9. Record observation and trace event.
10. Decide whether to continue, verify, or finish.
```

Termination conditions:

```text
model emits final_answer
verification passes and task is done
max_steps reached
max_tool_calls reached
max_patches reached
permission denied for required action
fatal tool error
same action repeated too many times
user cancels
```

Suggested B version limits:

```text
max_steps = 20
max_tool_calls = 30
max_patches = 5
max_shell_commands = 8
max_runtime_seconds = 600
```

If a limit is reached, the runtime must not claim success. It should produce a partial report with current evidence and the trace path.

## 8. AgentAction Protocol

All model outputs are normalized into `AgentAction`.

Supported B version action types:

```text
tool_call
patch_proposal
plan_update
ask_user
final_answer
```

### 8.1 `tool_call`

Example:

```json
{
  "type": "tool_call",
  "tool": "read_file",
  "arguments": {
    "path": "src/mikucode/parser.py",
    "start_line": 1,
    "end_line": 160
  },
  "reason": "Inspect parser implementation related to the failing test."
}
```

`reason` is a short user-visible rationale, not chain-of-thought.

### 8.2 `patch_proposal`

Example:

```json
{
  "type": "patch_proposal",
  "patches": [
    {
      "path": "src/mikucode/parser.py",
      "kind": "search_replace",
      "old_text": "return parse_raw(text)",
      "new_text": "return parse_raw(text.strip())"
    }
  ],
  "reason": "Normalize trailing whitespace before parsing."
}
```

The runtime validates and applies patches; the model does not directly write files.

### 8.3 `plan_update`

Example:

```json
{
  "type": "plan_update",
  "items": [
    {"status": "completed", "text": "Reproduced the failing parser test."},
    {"status": "in_progress", "text": "Inspect parser whitespace handling."},
    {"status": "pending", "text": "Apply minimal patch and rerun targeted tests."}
  ]
}
```

### 8.4 `ask_user`

Used only when a real user decision is required.

Example:

```json
{
  "type": "ask_user",
  "question": "Allow running `uv sync` to install missing dependencies?",
  "options": ["Allow once", "Deny", "Always allow uv sync in this project"],
  "risk_level": "medium"
}
```

### 8.5 `final_answer`

Example:

```json
{
  "type": "final_answer",
  "summary": "Fixed the parser whitespace bug.",
  "changed_files": ["src/mikucode/parser.py"],
  "verification": [
    {
      "command": "uv run pytest tests/test_parser.py",
      "exit_code": 0,
      "summary": "12 passed"
    }
  ],
  "remaining_risks": ["Only targeted parser tests were run; full suite was not executed."]
}
```

Final reports should be assembled from runtime evidence where possible. The model may summarize, but command names, exit codes, changed files, and trace paths must come from runtime state.

## 9. Tool Calling Protocol

MikuCode supports two tool calling strategies by design:

```text
JSON command mode
Native tool calling mode
```

B version default:

```text
JSON command mode first
Native tool calling reserved or experimental
```

Reason: OpenAI-compatible models vary in how well they implement native tool calling. JSON command mode is more portable across cloud APIs, local gateways, and domestic model providers.

### 9.1 JSON Command Mode

The model is instructed to output a single JSON object containing an `AgentAction`.

Invalid output handling:

```text
1. Extract JSON if surrounded by natural language.
2. Parse JSON.
3. Validate against AgentAction schema.
4. If invalid, request one JSON repair.
5. If still invalid, record ModelOutputError and stop or continue according to policy.
```

### 9.2 Native Tool Calling Mode

Reserved for C version or experimental B version. It uses OpenAI-style `tools` and `tool_calls`, then normalizes results into `AgentAction`.

The architecture should include an adapter boundary:

```text
ToolCallAdapter
  ├── JsonCommandAdapter
  └── NativeToolCallAdapter
```

## 10. ToolResult Protocol

Tools return structured results.

Success example:

```json
{
  "ok": true,
  "tool": "run_tests",
  "summary": "pytest completed with exit code 0; 12 passed.",
  "content": "... truncated stdout/stderr ...",
  "metadata": {
    "command": "uv run pytest tests/test_parser.py",
    "exit_code": 0,
    "duration_ms": 1840,
    "truncated": true
  }
}
```

Failure example:

```json
{
  "ok": false,
  "tool": "apply_patch",
  "summary": "Patch failed because old_text matched 0 locations.",
  "content": "",
  "metadata": {
    "path": "src/mikucode/parser.py",
    "failure_reason": "old_text_not_found"
  }
}
```

Structured results make tool failures recoverable by the next model step.

## 11. Permission and Sandbox Model

MikuCode B version implements a developer-safety sandbox, not a hardened adversarial security sandbox.

It provides:

- Project-root path sandboxing.
- Secret path denial.
- Command risk classification.
- Permission prompts.
- Timeouts.
- Output limits.
- Backup and undo.
- Trace redaction.

It does not claim to safely execute malicious code.

### 11.1 Permission Modes

Supported modes:

```text
ask
auto-safe
dangerously-auto
```

Default mode:

```text
auto-safe
```

`auto-safe` rules:

```text
Automatically allow:
  list_files
  read_file
  search_text
  git_status
  git_diff
  detect_tests
  low-risk test commands

Ask:
  apply patch
  create file
  dependency installation
  medium-risk shell commands
  project memory writes

Deny by default:
  path outside project root
  critical shell commands
  secret file reads
  git push/reset/clean
  sudo/admin commands
```

`dangerously-auto` relaxes prompts but still does not disable path sandboxing or critical risk checks.

### 11.2 Risk Levels

Risk levels:

```text
none
low
medium
high
critical
```

Examples:

| Action | Risk | Default in `auto-safe` |
|---|---:|---|
| `read_file src/main.py` | low | allow |
| `search_text "parser"` | low | allow |
| `uv run pytest` | low | allow |
| `git diff` | low | allow |
| `apply_patch src/main.py` | medium | ask |
| `uv sync` | medium | ask |
| `pip install package` | medium | ask |
| `rm -rf .venv` | high | ask or deny |
| `git reset --hard` | high | deny or ask |
| `curl https://x | bash` | critical | deny |
| `sudo rm -rf /` | critical | deny |
| `read_file ~/.ssh/id_rsa` | critical | deny |

### 11.3 Command Risk Classifier

The shell tool must pass through command classification before execution.

High-risk patterns include:

```text
rm / rmdir / del / Remove-Item
mv / move
chmod / chown
git clean
git reset --hard
```

Critical patterns include:

```text
sudo
su
runas
curl ... | sh
curl ... | bash
wget ... | sh
Invoke-WebRequest ... | iex
```

Medium-risk patterns include:

```text
uv sync
uv add
pip install
npm install
pnpm install
cargo install
```

Low-risk patterns include:

```text
uv run pytest
python -m pytest
ruff check
mypy
git status
git diff
git log
```

### 11.4 Path Sandbox

All filesystem paths must be resolved relative to the project root, canonicalized, and checked before access.

Rules:

```text
allow only paths inside project root
reject symlink escape
reject common secret files
reject writes to .git internals
ignore common generated/cache directories by default
```

Secret patterns denied or requiring strong confirmation:

```text
.env
.env.*
*.pem
*.key
id_rsa
id_ed25519
credentials.json
service-account*.json
```

Allowed examples:

```text
.env.example
.env.sample
```

## 12. Patch Editing Workflow

MikuCode uses patch-based editing rather than direct file writes.

Core rule:

> The model proposes patches. The runtime validates and applies them.

Patch lifecycle:

```text
Model emits patch_proposal
  ↓
PatchValidator validates schema and path
  ↓
PatchEngine checks file state
  ↓
DiffEngine generates preview
  ↓
PermissionPolicy decides allow/ask/deny
  ↓
BackupManager snapshots originals
  ↓
PatchEngine applies patch
  ↓
TraceRecorder records patch event
  ↓
Verification state becomes stale
```

### 12.1 `search_replace`

Validation rules:

```text
path inside project root
file exists
old_text is non-empty
old_text exactly matches once
new_text differs from old_text
file is not too large
file hash matches last-read hash if known
```

If `old_text` matches zero or multiple locations, the patch is rejected and the model should re-read the file.

### 12.2 `create_file`

Validation rules:

```text
path inside project root
parent directory exists or is explicitly approved for creation
if_exists defaults to fail
existing files are not overwritten without confirmation
```

### 12.3 Backup and Undo

Patch backups live in:

```text
.miku/backups/
.miku/patches/
```

Undo restores only MikuCode-applied patches. Before undoing, MikuCode checks whether the file was externally modified after the patch.

If an external modification is detected, automatic undo is refused or requires confirmation:

```text
File changed since MikuCode applied the patch. Refusing automatic undo to avoid overwriting user edits.
```

## 13. Verification Workflow

Verification is evidence-driven. MikuCode should not claim a task is complete without reporting what verification did or did not run.

Workflow:

```text
1. Detect project type.
2. Detect available test commands.
3. Select targeted verification if possible.
4. Run command through permissioned shell.
5. Capture exit code, stdout, stderr, and duration.
6. Summarize result.
7. Feed failures back into the agent loop.
8. Include evidence in the final report.
```

### 13.1 Python Test Detection

Because the target system uses `uv` for Python, MikuCode should prefer:

```bash
uv run pytest
```

Detection hints:

```text
pyproject.toml
uv.lock
pytest.ini
tox.ini
noxfile.py
tests/
```

Project override in `.miku/config.toml`:

```toml
[verification]
test_command = "uv run pytest"
lint_command = "uv run ruff check"
typecheck_command = "uv run mypy src"
```

### 13.2 Targeted Verification

MikuCode should prefer targeted verification before full-suite verification.

Examples:

```text
Failure mentions tests/test_parser.py
  → run uv run pytest tests/test_parser.py

Modified src/mikucode/parser.py
  → search for tests matching parser

No clear target
  → run default test command
```

The final report must distinguish targeted tests from full-suite tests.

### 13.3 Verification State

Patch application marks verification as stale.

Verification states:

```text
stale
passed
failed
skipped
unknown
```

Final report must include the latest verification state and evidence. If no verification ran, it must say why.

## 14. Context Management

MikuCode uses selective context building rather than whole-repository dumping.

ContextBuilder inputs:

```text
user task
current AgentState
project memory
session summary
recent tool observations
files read
files modified
git diff
test output
available tools
context budget
```

ContextBuilder output:

```text
model messages
action schema or tool definitions
selected file snippets
recent observation summary
current plan
safety instructions
```

B version can use character budgets rather than exact tokenization:

```text
max_context_chars = 60000
max_file_snippet_chars = 12000
max_observation_chars = 20000
```

Context priority:

```text
1. user goal
2. current plan
3. recent failures
4. changed file diff
5. project memory
6. relevant snippets
7. older observations summary
```

Relevant file ranking signals:

```text
user-mentioned paths or symbols
test failure stack paths
grep/search hits
import/module name matches
recently read or edited files
git diff files
tests/ and src/ filename correspondence
```

## 15. Memory System

MikuCode B version supports project memory and session memory.

### 15.1 Project Memory

Files:

```text
.miku/project.md
.miku/config.toml
.miku/memory.json
```

Example `project.md`:

```markdown
# MikuCode Project Memory

## Commands
- Test: uv run pytest
- Lint: uv run ruff check

## Conventions
- Use pathlib for filesystem code.
- Do not edit generated files.
```

Project memory writes should require confirmation unless the user explicitly commands them.

Do not write secrets, temporary logs, unverified guesses, or one-off debugging details into project memory.

### 15.2 Session Memory

Session memory is internal runtime state:

```text
task goal
step count
current plan
files read
files edited
tool results
patch history
verification results
permission decisions
```

It is saved through traces and session state.

## 16. Tracing and Replay

Every session writes JSONL trace events to:

```text
.miku/sessions/<timestamp>-session.jsonl
```

Event types:

```text
session_started
user_task
state_transition
context_built
model_request
model_response
action_parsed
validation_failed
permission_decision
tool_call
tool_result
patch_proposed
patch_applied
verification_started
verification_result
final_report
session_stopped
```

Trace entries must be redacted before writing. Basic redaction patterns:

```text
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
Authorization: Bearer ...
sk-...
api_key=...
token=...
password=...
```

B version replay command:

```bash
miku trace show .miku/sessions/session.jsonl
```

It should display a compact timeline of user task, tool calls, patches, verification, and final report.

## 17. Benchmark Harness

B version includes a smoke benchmark, not a large research benchmark.

Directory shape:

```text
benchmarks/
  smoke/
    parser_bug/
      task.md
      repo/
      expected.patch
      verify.sh
```

Command:

```bash
miku bench smoke
```

Metrics:

```text
success rate
number of steps
number of tool calls
number of shell commands
number of patches
verification result
duration
trace path
estimated token usage if available
```

Benchmark tasks should be small, deterministic, and locally verifiable.

## 18. CLI and REPL UX

Example REPL flow:

```text
$ miku chat

MikuCode > fix failing parser tests

● Building context
● Running: uv run pytest
✗ tests/test_parser.py failed

● Reading tests/test_parser.py
● Reading src/mikucode/parser.py

Proposed patch:
  src/mikucode/parser.py

--- before
+++ after
- return parse_raw(text)
+ return parse_raw(text.strip())

Apply patch? [y/N] y

● Running: uv run pytest tests/test_parser.py
✓ 12 passed

Done.
Changed files:
  src/mikucode/parser.py

Verification:
  uv run pytest tests/test_parser.py
  exit code: 0
```

The UX should show action traces, but not hidden chain-of-thought.

## 19. Testing Strategy

MikuCode must test its own runtime rigorously.

Unit tests:

```text
ActionParser
ToolRegistry
PathSandbox
CommandRiskClassifier
PatchValidator
PatchEngine
PermissionPolicy
VerificationDetector
TraceRecorder
MemoryStore
```

Integration tests should use temporary repositories and `MockProvider`.

Mock model action sequence example:

```text
1. run_tests
2. read_file
3. patch_proposal
4. run_tests
5. final_answer
```

Golden trace tests should assert event order and required fields.

## 20. 4–6 Week Implementation Milestones

### Week 1: Project skeleton and CLI

Deliver:

```text
pyproject.toml
src/mikucode/
Typer CLI
Rich console
miku init
miku chat shell
ToolRegistry skeleton
basic tests
```

Done when:

```text
uv run miku --help works
uv run pytest works
.miku/ initialization works
mock tool registration works
```

### Week 2: Agent loop and model provider

Deliver:

```text
AgentRuntime
AgentState
AgentAction
JsonCommandAdapter
ModelProvider
OpenAICompatibleProvider
MockProvider
max_steps
trace events
```

Done when:

```text
MockProvider drives a full loop
invalid JSON path is handled
max_steps stops runaway loops
OpenAI-compatible provider reads config/env
```

### Week 3: Filesystem tools and context builder

Deliver:

```text
list_files
read_file
search_text
file tree summary
basic ranking
path sandbox
ContextBuilder v1
```

Done when:

```text
agent can search and read relevant files
outside-project paths are denied
context remains bounded
trace records read/search actions
```

### Week 4: Patch editing, diff, backup, undo, permission

Deliver:

```text
patch_proposal
search_replace patch
create_file patch
diff preview
backup manager
undo manager
PermissionPolicy
RiskLevel
```

Done when:

```text
patches require exact unique old_text match
diff is shown before apply
backup is created before apply
undo restores MikuCode patches
external modifications prevent silent undo
```

### Week 5: Shell, verification, memory, trace

Deliver:

```text
run_shell
run_tests
detect_tests
CommandRiskClassifier
VerificationEngine
ProjectMemory
SessionMemory
TraceRecorder
secret redaction
```

Done when:

```text
uv run pytest can be run through permissioned shell
dangerous commands are blocked
test evidence enters final report
trace JSONL is complete and redacted
```

### Week 6: Benchmark, docs, demo, resume material

Deliver:

```text
miku bench smoke
example buggy project
README
architecture doc
flagship roadmap doc
demo script or video
resume bullets
```

Done when:

```text
smoke benchmark runs
README shows demo and safety model
architecture is documented
C roadmap is documented
```

## 21. B Version Acceptance Criteria

The B version is complete when:

```text
1. uv run miku chat enters REPL.
2. uv run miku "fix failing tests" runs one-shot mode.
3. Agent can search, read files, and run tests.
4. Agent can propose patch_proposal.
5. User can review diff and confirm application.
6. Patch creates backup and can be undone.
7. Shell commands use risk classification and timeout.
8. Paths outside project root are denied.
9. Verification result enters final report.
10. JSONL trace can be viewed.
11. Smoke benchmark runs.
12. README includes demo, architecture, safety model, and roadmap.
13. Core runtime modules have tests.
```

## 22. Flagship Roadmap: 8–10 Week C Version

The flagship version upgrades MikuCode from a local CLI runtime into an agent development platform.

### Phase 1: Web trace dashboard

Goal: visualize JSONL traces.

Features:

```text
session list
timeline view
tool call detail
diff viewer
verification panel
permission decisions
cost/token estimates
```

Suggested stack:

```text
FastAPI backend
React/Vite frontend
```

### Phase 2: MCP-like plugin protocol

Goal: allow tools to be served by external processes.

Minimal protocol:

```text
list_tools
call_tool
tool_schema
capabilities
```

Potential plugins:

```text
GitHub
Browser
Database
Vercel
Issue tracker
```

### Phase 3: Multi-agent roles

Goal: support role-based modes before true autonomous multi-agent execution.

Modes:

```text
miku debug
miku review
miku implement
miku test
```

Each mode has:

```text
system prompt
allowed tools
verification policy
risk tolerance
done criteria
```

### Phase 4: Container sandbox

Goal: upgrade shell execution from developer-safety sandbox to stronger isolation.

Approach:

```text
Docker-based sandbox
project mounted as workspace
network disabled by default
resource limits
timeouts
clean environment
```

### Phase 5: Advanced verification planner

Goal: cascade verification.

```text
targeted tests
related package tests
lint/typecheck
full suite
```

### Phase 6: Advanced benchmark reports

Compare:

```text
JSON command mode vs native tool calling
Model A vs Model B
Context strategy A vs B
Permission strict vs auto-safe
search_replace vs unified diff patching
```

Output:

```text
HTML report
CSV/JSON export
trace links for failures
```

### Phase 7: IDE integration prototype

Goal: demonstrate architecture extensibility.

Possible scope:

```text
VS Code task integration
open trace dashboard from workspace
run miku on selected file
apply CLI-generated diff
```

## 23. Risks and Mitigations

### Risk: Scope creep

Mitigation:

```text
B version only implements the CLI runtime loop.
Web, IDE, MCP, multi-agent, and Docker stay in C roadmap.
```

### Risk: Model output instability

Mitigation:

```text
JSON extraction
schema validation
one-shot repair
MockProvider tests
structured error observations
```

### Risk: File editing damages user work

Mitigation:

```text
old_text unique match
file hash checks
diff preview
backup
undo
external modification detection
```

### Risk: Shell commands are dangerous

Mitigation:

```text
CommandRiskClassifier
PermissionPolicy
critical deny list
timeouts
project cwd lock
```

### Risk: Verification hallucination

Mitigation:

```text
final report assembled from runtime evidence
exit codes come from ToolResult metadata
unverified work is explicitly reported as unverified
```

### Risk: Trace leaks secrets

Mitigation:

```text
secret file denial
trace redaction
stdout/stderr redaction
no automatic project memory writes for secrets
```

## 24. README and Demo Plan

README sections:

```text
# MikuCode
Demo GIF / video
Highlights
Quickstart with uv
Example: fixing a failing test
Architecture
Safety model
Benchmark results
Flagship roadmap
Resume notes
```

Demo scenario:

```text
1. Open a small Python project with a failing parser test.
2. Run uv run miku chat.
3. Ask: fix failing parser tests.
4. MikuCode runs targeted tests.
5. MikuCode reads failing test and source file.
6. MikuCode proposes patch.
7. User reviews diff and accepts.
8. MikuCode runs uv run pytest tests/test_parser.py.
9. Tests pass.
10. Show /diff, /trace, and /undo.
```

## 25. Resume Bullets

English:

```text
- Built MikuCode, a Python-based local coding agent runtime inspired by Claude Code/Codex, using an OpenAI-compatible model layer and structured JSON action protocol.
- Designed a permissioned tool execution system with path sandboxing, command risk classification, patch-based editing, diff preview, backups, and undo.
- Implemented context selection, project/session memory, replayable JSONL traces, and evidence-driven verification with uv run pytest.
- Added a smoke benchmark harness measuring success rate, tool calls, patch count, verification outcome, and session duration.
```

Chinese:

```text
- 设计并实现 MikuCode，一个 Python 本地 coding agent runtime，采用 OpenAI-compatible 模型层和结构化 JSON action 协议。
- 实现权限化工具执行系统，包括路径沙箱、命令风险分类、patch-based editing、diff preview、backup 与 undo。
- 实现上下文选择、项目/会话记忆、可重放 JSONL trace，以及基于 uv run pytest 的证据驱动验证工作流。
- 构建 smoke benchmark，统计成功率、工具调用次数、补丁数量、验证结果和执行耗时。
```

## 26. Interview Pitch

Chinese:

> MikuCode 不是代码生成器，而是本地 agent runtime。LLM 只负责提出结构化动作，runtime 负责校验、权限、执行、追踪、回滚和验证。这种分离让系统可以安全失败：JSON 错了可以修复，危险命令会被拦截，patch 冲突会拒绝，测试失败会回填给模型，最终报告基于真实命令证据。

English:

> MikuCode is not a code generator; it is a local agent runtime. The LLM emits structured actions, while the runtime handles validation, permissions, execution, tracing, rollback, and verification. This separation lets the system fail safely: invalid JSON can be repaired, unsafe commands are blocked, patch conflicts are rejected, failed tests feed back into the loop, and final reports are grounded in real command evidence.

## 27. Implementation Gate

This design is ready for review. After user approval, the next step is to create an implementation plan with the `superpowers:writing-plans` skill.

Because the current directory is not a git repository, this design document cannot be committed in this session. If the project is later initialized with git, this spec should be committed as the first architecture artifact.
