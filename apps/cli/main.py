import asyncio

import typer

from rich.console import Console
from rich.panel import Panel

from assist_runtime.services.chat_service import ChatService

app = typer.Typer()

console = Console()

def version_callback(version: bool):
    """
    Show version
    """
    if version:
        console.print(
            "[bold green]Jarvis Runtime v0.1.0[/bold green]"
        )
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def jarvis(
    ctx: typer.Context,
    prompt: list[str] = typer.Argument(None),
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_flag=True,
        help="Show version"
    )
):
    """
    Natural language Jarvis runtime
    """

    if ctx.invoked_subcommand:
        return

    if not prompt:
        console.print(
            "[bold red]Please provide a prompt[/bold red]"
        )
        raise typer.Exit()

    service = ChatService()

    user_prompt = " ".join(prompt)

    result = asyncio.run(
        service.chat(user_prompt)
    )

    console.print(
        Panel.fit(
            result,
            title="Jarvis"
        )
    )



if __name__ == "__main__":
    app()