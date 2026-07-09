from rich.console import Console

from mikucode.runtime.state import AgentState


def print_agent_result(console: Console, state: AgentState, *, max_observations: int = 12) -> None:
    """Print run outcome with enough tool evidence for the user to trust results."""
    if state.done:
        console.print("[green]Done.[/green]")
    else:
        console.print("[yellow]Stopped.[/yellow]")
        if state.files_modified:
            changed = ", ".join(sorted(state.files_modified))
            console.print(
                "[yellow]Note:[/yellow] no final_answer before stop, "
                f"but these files were modified: {changed}"
            )
        console.print(f"[dim]steps={state.step_count} observations={len(state.observations)}[/dim]")

    observations = state.observations
    if not observations:
        return
    if len(observations) > max_observations:
        console.print(
            f"[dim](showing last {max_observations} of {len(observations)} observations)[/dim]"
        )
        observations = observations[-max_observations:]

    for observation in observations:
        if observation.tool == "final_answer":
            console.print(observation.summary)
        elif observation.ok:
            console.print(f"[dim]{observation.tool}:[/dim] {observation.summary}")
        else:
            console.print(f"[red]{observation.tool}:[/red] {observation.summary}")
