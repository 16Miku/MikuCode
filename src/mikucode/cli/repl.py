from pathlib import Path

from rich.console import Console

from mikucode.cli.display import print_agent_result
from mikucode.cli.factory import build_provider, build_registry
from mikucode.config import load_config
from mikucode.editing.undo import UndoManager
from mikucode.runtime.agent import AgentRuntime


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
            if user_input == "/undo":
                result = UndoManager(self.config.project_root).undo_last()
                self.console.print(result.summary)
                continue
            try:
                runtime = AgentRuntime(
                    project_root=self.config.project_root,
                    provider=build_provider(),
                    registry=build_registry(self.config.project_root),
                )
                state = runtime.run(user_input)
            except Exception as exc:
                self.console.print(f"[red]Runtime error:[/red] {exc}")
                continue
            print_agent_result(self.console, state)
