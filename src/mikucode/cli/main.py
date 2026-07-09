from pathlib import Path
from typing import List

import typer
from rich.console import Console

from mikucode.cli.repl import MikuRepl
from mikucode.config import ensure_miku_dir

app = typer.Typer(help="MikuCode local coding agent runtime")
console = Console()


def _dispatch_init(project_root: Path) -> None:
    miku_dir = ensure_miku_dir(project_root)
    console.print(f"Initialized MikuCode at [bold]{miku_dir}[/bold]")


def _dispatch_chat(project_root: Path) -> None:
    repl = MikuRepl(project_root=project_root, console=console)
    repl.run()


@app.command()
def main(
    args: List[str] = typer.Argument(None, help="Command or one-shot task for MikuCode"),
    project_root: Path = typer.Option(Path.cwd(), help="Project root"),
) -> None:
    if not args:
        console.print("MikuCode local coding agent runtime")
        console.print("Usage: miku init | miku chat | miku <task>")
        return

    command = args[0]
    if command == "init":
        _dispatch_init(project_root)
        return

    if command == "chat":
        _dispatch_chat(project_root)
        return

    task = " ".join(args).strip()
    ensure_miku_dir(project_root)
    console.print(f"One-shot runtime is not connected yet. Task received: {task}")
