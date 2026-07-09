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
