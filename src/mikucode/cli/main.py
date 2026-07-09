from pathlib import Path
from typing import List

import typer
from rich.console import Console

from mikucode.benchmark.smoke import run_smoke_benchmark
from mikucode.cli.factory import build_provider, build_registry
from mikucode.cli.repl import MikuRepl
from mikucode.config import ensure_miku_dir
from mikucode.editing.undo import UndoManager
from mikucode.runtime.agent import AgentRuntime
from mikucode.tracing.replay import render_trace

app = typer.Typer(
    help=(
        "MikuCode local coding agent runtime. "
        "Commands: init | chat | undo | trace show <path> | bench smoke | <task>."
    )
)
console = Console()


def _dispatch_init(project_root: Path) -> None:
    miku_dir = ensure_miku_dir(project_root)
    console.print(f"Initialized MikuCode at [bold]{miku_dir}[/bold]")


def _dispatch_chat(project_root: Path) -> None:
    repl = MikuRepl(project_root=project_root, console=console)
    repl.run()


def _dispatch_undo(project_root: Path) -> None:
    ensure_miku_dir(project_root)
    result = UndoManager(project_root).undo_last()
    console.print(result.summary)


def _dispatch_trace(args: List[str]) -> None:
    if not args or args[0] != "show":
        console.print("Usage: miku trace show <path>")
        raise typer.Exit(code=1)
    if len(args) < 2:
        console.print("Usage: miku trace show <path>")
        raise typer.Exit(code=1)
    path = Path(args[1])
    if not path.exists():
        console.print(f"[red]Trace file not found:[/red] {path}")
        raise typer.Exit(code=1)
    console.print(render_trace(path))


def _dispatch_bench(args: List[str], project_root: Path) -> None:
    if not args or args[0] != "smoke":
        console.print("Usage: miku bench smoke")
        raise typer.Exit(code=1)
    result = run_smoke_benchmark(project_root)
    console.print(result)


def _dispatch_one_shot(project_root: Path, task: str) -> None:
    ensure_miku_dir(project_root)
    try:
        runtime = AgentRuntime(
            project_root=project_root,
            provider=build_provider(),
            registry=build_registry(project_root),
        )
        state = runtime.run(task)
    except Exception as exc:
        console.print(f"[red]Runtime error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if state.done:
        console.print("[green]Done.[/green]")
    else:
        console.print("[yellow]Stopped.[/yellow]")
    for observation in state.observations[-3:]:
        console.print(observation.summary)


@app.command()
def main(
    args: List[str] = typer.Argument(
        None,
        help=(
            "Command or one-shot task. "
            "Built-ins: init, chat, undo, trace show <path>, bench smoke; "
            "anything else is a free-form one-shot task."
        ),
    ),
    project_root: Path = typer.Option(Path.cwd(), help="Project root"),
) -> None:
    """MikuCode CLI: init, chat, undo, trace show, bench smoke, or free-form task."""
    if not args:
        console.print("MikuCode local coding agent runtime")
        console.print(
            "Usage: miku init | miku chat | miku undo | miku trace show <path> | "
            "miku bench smoke | miku <task>"
        )
        return

    command = args[0]
    if command == "init":
        _dispatch_init(project_root)
        return

    if command == "chat":
        _dispatch_chat(project_root)
        return

    if command == "undo":
        _dispatch_undo(project_root)
        return

    if command == "trace":
        _dispatch_trace(args[1:])
        return

    if command == "bench":
        _dispatch_bench(args[1:], project_root)
        return

    task = " ".join(args).strip()
    _dispatch_one_shot(project_root, task)
