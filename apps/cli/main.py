import asyncio
import logging
import typer

from rich.console import Console
from rich.panel import Panel

from assist_runtime.services.chat_service import ChatService
from assist_runtime.config.logging import setup_logging
from assist_runtime.workflows.repo_analysis.workflow import RepoAnalysisWorkflow
from assist_runtime.workflows.document_summary.workflow import DocumentSummaryWorkflow
from assist_runtime.workflows.repo_qa.workflow import RepoQAWorkflow
from assist_runtime.workflows.state import WorkflowState
from assist_runtime.llm.client import UnifiedLLMClient
from assist_runtime.memory.embedders.sentence_transformer import SentenceTransformerEmbedder
from assist_runtime.memory.vector_store.chroma import ChromaVectorStore
from assist_runtime.memory.retrieval.retriever import Retriever

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


@app.command()
def analyze(
    repo_path: str = typer.Argument(".", help="Path to repository to analyze")
):
    """Run the repository analysis workflow."""
    console.print(f"[bold cyan]Starting Repo Analysis on {repo_path}...[/bold cyan]")
    workflow = RepoAnalysisWorkflow()
    llm_client = UnifiedLLMClient()
    
    state = WorkflowState(
        workflow_name="repo_analysis",
        metadata={"repo_path": repo_path, "llm_client": llm_client}
    )
    
    result = asyncio.run(workflow.run(state))
    if result.success:
        console.print(f"[bold green]Success![/bold green] Artifact generated at: {result.artifacts[0] if result.artifacts else 'none'}")
    else:
        console.print(f"[bold red]Failed:[/bold red] {result.error}")

@app.command()
def summarize(
    files: list[str] = typer.Argument(..., help="Files to summarize")
):
    """Run the document summarization workflow."""
    console.print(f"[bold cyan]Starting Document Summarization...[/bold cyan]")
    workflow = DocumentSummaryWorkflow()
    llm_client = UnifiedLLMClient()
    
    state = WorkflowState(
        workflow_name="document_summary",
        metadata={"file_paths": files, "llm_client": llm_client}
    )
    
    result = asyncio.run(workflow.run(state))
    if result.success:
        console.print(f"[bold green]Success![/bold green] Artifact generated at: {result.artifacts[0] if result.artifacts else 'none'}")
    else:
        console.print(f"[bold red]Failed:[/bold red] {result.error}")

@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask"),
    repo_path: str = typer.Option(".", help="Repository context path")
):
    """Ask a question about the repository using Q&A workflow."""
    console.print(f"[bold cyan]Answering question: {question}[/bold cyan]")
    workflow = RepoQAWorkflow()
    llm_client = UnifiedLLMClient()
    embedder = SentenceTransformerEmbedder()
    vector_store = ChromaVectorStore()
    retriever = Retriever(embedder=embedder, vector_store=vector_store)
    
    state = WorkflowState(
        workflow_name="repo_qa",
        goal=question,
        metadata={"repo_path": repo_path, "llm_client": llm_client, "retriever": retriever}
    )
    
    result = asyncio.run(workflow.run(state))
    if result.success:
        console.print(f"[bold green]Success![/bold green] Answer recorded.")
    else:
        console.print(f"[bold red]Failed:[/bold red] {result.error}")

if __name__ == "__main__":
    app()