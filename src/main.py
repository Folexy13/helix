"""
Helix - Intelligence That Spirals Forward

Main application entry point.
Provides CLI and API interfaces for interacting with Helix.
"""

import asyncio
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.core.config import settings
from src.core.models import AgentRole, Conversation, SessionState
from src.agents.pillar1.router import RouterAgent
from src.agents.pillar2.orchestrator import OrchestratorAgent
from src.agents.pillar3.sage import SageAgent
from src.agents.base import AgentContext
from src.hitl.checkpoint_manager import CheckpointManager
from src.hitl.handlers import ConsoleHITLHandler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.value),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# CLI app
app = typer.Typer(
    name="helix",
    help="Helix - Intelligence That Spirals Forward",
    add_completion=False,
)

# Rich console for pretty output
console = Console()


def print_banner():
    """Print the Helix banner."""
    banner = """
    ██╗  ██╗███████╗██╗     ██╗██╗  ██╗
    ██║  ██║██╔════╝██║     ██║╚██╗██╔╝
    ███████║█████╗  ██║     ██║ ╚███╔╝ 
    ██╔══██║██╔══╝  ██║     ██║ ██╔██╗ 
    ██║  ██║███████╗███████╗██║██╔╝ ██╗
    ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝
    
    Intelligence That Spirals Forward
    Powered by Amazon Nova
    """
    console.print(Panel(banner, style="bold blue"))


@app.command()
def startup(
    idea: Optional[str] = typer.Argument(None, help="Your startup idea"),
    voice: bool = typer.Option(False, "--voice", "-v", help="Enable voice mode"),
):
    """
    Pillar 1: Analyze a startup idea with the Founding Team.
    
    The AI founding team (ARIA, FELIX, NOVA, JUDGE) will analyze your idea
    and produce a comprehensive Startup Brief.
    """
    print_banner()
    console.print("\n[bold green]🚀 Pillar 1: The Founding Team[/bold green]\n")
    
    if not idea:
        idea = typer.prompt("Describe your startup idea")
    
    asyncio.run(_run_pillar1(idea, voice))


@app.command()
def build(
    feature: Optional[str] = typer.Argument(None, help="Feature to build"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Repository path"),
    voice: bool = typer.Option(False, "--voice", "-v", help="Enable voice mode"),
):
    """
    Pillar 2: Build a feature with the Engineering Workforce.
    
    The engineering team (PLANNER, CODER, TESTER, DOCS, REVIEWER) will
    implement your feature and create a GitHub PR.
    """
    print_banner()
    console.print("\n[bold green]🔧 Pillar 2: The Engineering Workforce[/bold green]\n")
    
    if not feature:
        feature = typer.prompt("Describe the feature to build")
    
    asyncio.run(_run_pillar2(feature, repo, voice))


@app.command()
def ask(
    question: Optional[str] = typer.Argument(None, help="Question about your codebase"),
    repo: str = typer.Option(".", "--repo", "-r", help="Repository path"),
    voice: bool = typer.Option(False, "--voice", "-v", help="Enable voice mode"),
):
    """
    Pillar 3: Ask questions about your codebase with SAGE.
    
    SAGE will index your codebase and answer questions using
    Nova Multimodal Embeddings for semantic understanding.
    """
    print_banner()
    console.print("\n[bold green]🧠 Pillar 3: Codebase Intelligence[/bold green]\n")
    
    if not question:
        question = typer.prompt("What would you like to know about your codebase?")
    
    asyncio.run(_run_pillar3(question, repo, voice))


@app.command()
def interactive():
    """
    Start an interactive Helix session.
    
    Access all three pillars in one unified interface.
    """
    print_banner()
    console.print("\n[bold green]🌀 Interactive Helix Session[/bold green]\n")
    console.print("Commands: [startup], [build], [ask], [quit]\n")
    
    asyncio.run(_run_interactive())


async def _run_pillar1(idea: str, voice: bool = False):
    """Run Pillar 1 - Founding Team analysis."""
    # Create session state
    session_state = SessionState()
    
    # Create checkpoint manager
    checkpoint_manager = CheckpointManager(session_state)
    hitl_handler = ConsoleHITLHandler(checkpoint_manager)
    
    # Create router agent
    router = RouterAgent()
    
    # Create context
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar1_conversation,
        user_input=idea,
    )
    
    console.print(f"\n[bold]Analyzing your idea:[/bold] {idea}\n")
    console.print("[dim]The Founding Team is assembling...[/dim]\n")
    
    try:
        # Execute the router
        response = await router.execute(context)
        
        # Handle HITL checkpoints
        while response.hitl_checkpoint and not response.hitl_checkpoint.is_resolved:
            checkpoint = response.hitl_checkpoint
            decision = await hitl_handler.present_checkpoint(checkpoint)
            
            # Get additional input if needed
            user_input = None
            if decision in [HITLDecision.EDIT, HITLDecision.EXPLAIN]:
                user_input = await hitl_handler.get_user_input("Please provide details")
            
            # Resolve checkpoint
            checkpoint_manager.resolve_checkpoint(checkpoint.id, decision, user_input)
            
            # Continue execution
            context.metadata["clarification_complete"] = True
            response = await router.execute(context)
        
        # Display result
        console.print(Panel(
            Markdown(response.content),
            title="[bold green]Helix Startup Brief[/bold green]",
            border_style="green",
        ))
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Pillar 1 error")


async def _run_pillar2(feature: str, repo: Optional[str], voice: bool = False):
    """Run Pillar 2 - Engineering Workforce."""
    # Create session state
    session_state = SessionState()
    
    # Create checkpoint manager
    checkpoint_manager = CheckpointManager(session_state)
    hitl_handler = ConsoleHITLHandler(checkpoint_manager)
    
    # Create orchestrator agent
    orchestrator = OrchestratorAgent()
    
    # Create context
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar2_conversation,
        user_input=feature,
        metadata={"repository_path": repo} if repo else {},
    )
    
    console.print(f"\n[bold]Building feature:[/bold] {feature}\n")
    console.print("[dim]The Engineering Workforce is assembling...[/dim]\n")
    
    try:
        # Execute the orchestrator
        response = await orchestrator.execute(context)
        
        # Handle HITL checkpoints
        while response.hitl_checkpoint and not response.hitl_checkpoint.is_resolved:
            checkpoint = response.hitl_checkpoint
            decision = await hitl_handler.present_checkpoint(checkpoint)
            
            user_input = None
            if decision in [HITLDecision.EDIT, HITLDecision.EXPLAIN]:
                user_input = await hitl_handler.get_user_input("Please provide details")
            
            checkpoint_manager.resolve_checkpoint(checkpoint.id, decision, user_input)
            
            context.metadata["intake_complete"] = True
            response = await orchestrator.execute(context)
        
        # Display result
        console.print(Panel(
            Markdown(response.content),
            title="[bold green]Engineering Output[/bold green]",
            border_style="green",
        ))
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Pillar 2 error")


async def _run_pillar3(question: str, repo: str, voice: bool = False):
    """Run Pillar 3 - Codebase Intelligence."""
    # Create session state
    session_state = SessionState()
    
    # Create checkpoint manager
    checkpoint_manager = CheckpointManager(session_state)
    hitl_handler = ConsoleHITLHandler(checkpoint_manager)
    
    # Create SAGE agent
    sage = SageAgent()
    
    # Index the repository
    console.print(f"\n[dim]Indexing repository: {repo}[/dim]\n")
    
    try:
        index = await sage.index_repository(repo)
        console.print(f"[green]✓ Indexed {len(index.indexed_files)} files[/green]\n")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not index repository: {e}[/yellow]\n")
    
    # Create context
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar3_conversation,
        user_input=question,
        metadata={"repository_path": repo},
    )
    
    console.print(f"\n[bold]Your question:[/bold] {question}\n")
    console.print("[dim]SAGE is analyzing the codebase...[/dim]\n")
    
    try:
        # Execute SAGE
        response = await sage.execute(context)
        
        # Handle HITL checkpoints
        while response.hitl_checkpoint and not response.hitl_checkpoint.is_resolved:
            checkpoint = response.hitl_checkpoint
            decision = await hitl_handler.present_checkpoint(checkpoint)
            
            user_input = None
            if decision == HITLDecision.APPROVE:
                user_input = await hitl_handler.get_user_input("Please clarify your question")
            
            checkpoint_manager.resolve_checkpoint(checkpoint.id, decision, user_input)
            
            context.user_input = user_input or question
            response = await sage.execute(context)
        
        # Display result
        console.print(Panel(
            Markdown(response.content),
            title="[bold green]SAGE's Answer[/bold green]",
            border_style="green",
        ))
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Pillar 3 error")


async def _run_interactive():
    """Run interactive session."""
    session_state = SessionState()
    
    while True:
        try:
            command = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: input("\n[helix] > ").strip().lower()
            )
            
            if command in ["quit", "exit", "q"]:
                console.print("\n[bold]Goodbye! 👋[/bold]\n")
                break
            
            elif command == "startup":
                idea = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: input("Your startup idea: ").strip()
                )
                await _run_pillar1(idea)
            
            elif command == "build":
                feature = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: input("Feature to build: ").strip()
                )
                await _run_pillar2(feature, None)
            
            elif command == "ask":
                question = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: input("Your question: ").strip()
                )
                await _run_pillar3(question, ".")
            
            else:
                console.print("[yellow]Unknown command. Try: startup, build, ask, quit[/yellow]")
                
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold]Goodbye! 👋[/bold]\n")
            break


@app.command()
def version():
    """Show Helix version information."""
    from src import __version__
    
    console.print(f"\n[bold]Helix[/bold] v{__version__}")
    console.print("Powered by Amazon Nova")
    console.print("Built for the Amazon Nova AI Hackathon, March 2026\n")


@app.command()
def status():
    """Show system status and configuration."""
    console.print("\n[bold]Helix System Status[/bold]\n")
    
    console.print(f"  AWS Region: {settings.aws_region}")
    console.print(f"  Nova Lite Model: {settings.nova_lite_model_id}")
    console.print(f"  Nova Sonic Model: {settings.nova_sonic_model_id}")
    console.print(f"  Nova Embeddings: {settings.nova_embeddings_model_id}")
    console.print(f"  Environment: {settings.environment.value}")
    console.print(f"  Debug Mode: {settings.debug}")
    console.print()


# Import HITLDecision for the handlers
from src.core.models import HITLDecision


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
