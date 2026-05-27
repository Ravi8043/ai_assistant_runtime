import asyncio
import logging
import typer

from rich.console import Console
from rich.panel import Panel

from assist_runtime.services.chat_service import ChatService
from assist_runtime.config.logging import setup_logging

setup_logging(debug_mode=True)

logger = logging.getLogger(__name__)

logger.info("Application started :) \n")

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

    service = ChatService()

    # One-shot mode
    if prompt:

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

        return

    # REPL mode
    console.print(
        "[bold green]Jarvis Runtime Started[/bold green]"
    )

    console.print(
        "[dim]Type 'exit' or 'quit' to stop[/dim]"
    )

    while True:

        try:

            user_prompt = console.input(
                "\n[bold cyan]> [/bold cyan]"
            ).strip()

            if not user_prompt:
                continue

            if user_prompt.lower() in [
                "exit",
                "quit"
            ]:

                console.print(
                    "[bold red]Shutting down Jarvis...[/bold red]"
                )

                break

            result = asyncio.run(
                service.chat(user_prompt)
            )

            console.print(
                Panel.fit(
                    result,
                    title="Jarvis"
                )
            )

        except KeyboardInterrupt:

            console.print(
                "\n[bold red]Interrupted[/bold red]"
            )

            break

        except Exception as error:

            console.print(
                f"[bold red]Error:[/bold red] {error}"
            )


if __name__ == "__main__":
    app()