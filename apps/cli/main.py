import asyncio

import typer

from rich.console import Console
from rich.panel import Panel

from assist_runtime.services.chat_service import ChatService

app = typer.Typer()

console = Console()


@app.command()
def chat(
    message: str
):
    """
    Chat with Jarvis
    """

    service = ChatService()

    result = asyncio.run(
        service.chat(message)
    )

    console.print(
        Panel.fit(
            result,
            title="Jarvis"
        )
    )


@app.command()
def version():
    """
    Show version
    """

    console.print(
        "[bold green]Jarvis Runtime v0.1.0[/bold green]"
    )


if __name__ == "__main__":
    app()