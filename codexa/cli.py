"""Main CLI entry point for Codexa."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional
from pathlib import Path

from .config import Config
# Import enhanced features if available, fallback to basic
try:
    from .enhanced_core import EnhancedCodexaAgent as CodexaAgent
    from .display.ascii_art import ASCIIArtRenderer, LogoTheme
    from .display.enhanced_startup import EnhancedStartup
    from .display.enhanced_ui import EnhancedUI, get_theme
    ENHANCED_FEATURES = True
except ImportError:
    from .core import CodexaAgent
    ENHANCED_FEATURES = False

console = Console()
app = typer.Typer(
    name="codexa",
    help="Codexa - AI-powered CLI coding assistant",
    no_args_is_help=False,
    invoke_without_command=True
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit")
) -> None:
    """
    Codexa: AI-powered CLI coding assistant.
    
    Run 'codexa' in any directory to start an interactive coding session.
    Codexa will create structured plans, requirements, and tasks for your projects.
    """
    if version:
        from . import __version__
        console.print(f"Codexa version {__version__}")
        return
    
    if ctx.invoked_subcommand is None:
        # Check configuration first
        config = Config()
        if not config.has_valid_config():
            show_setup_instructions()
            return
        
        # Start interactive session
        try:
            agent = CodexaAgent()
            
            # Show enhanced startup if available
            if ENHANCED_FEATURES:
                try:
                    import asyncio
                    startup = EnhancedStartup(console, "default")
                    
                    # Show startup sequence and welcome screen
                    async def enhanced_startup():
                        await startup.show_startup_sequence()
                        startup.show_welcome_screen()
                        await agent.start_session()
                    
                    asyncio.run(enhanced_startup())
                except Exception as e:
                    console.print(f"[yellow]Enhanced startup failed, using basic mode: {e}[/yellow]")
                    # Fallback to basic startup
                    try:
                        ascii_art = ASCIIArtRenderer()
                        logo = ascii_art.render_logo(LogoTheme.DEFAULT)
                        console.print(logo)
                    except Exception:
                        pass  # Fallback to basic startup
                    
                    import asyncio
                    asyncio.run(agent.start_session())
            else:
                agent.start_session()
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


@app.command()
def init() -> None:
    """Initialize Codexa in the current directory."""
    try:
        agent = CodexaAgent()
        agent.initialize_project()
        console.print("[green]✅ Codexa initialized successfully![/green]")
    except Exception as e:
        console.print(f"[red]Error initializing Codexa: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config() -> None:
    """Show current configuration and setup instructions."""
    config = Config()
    
    panel_content = Text()
    panel_content.append("Current Configuration:\n\n", style="bold")
    
    # Provider info
    provider = config.get_provider()
    panel_content.append(f"Provider: {provider}\n", style="blue")
    panel_content.append(f"Model: {config.get_model()}\n", style="blue")
    
    # API Key status
    openai_key = "✅ Configured" if config.openai_api_key else "❌ Not set"
    anthropic_key = "✅ Configured" if config.anthropic_api_key else "❌ Not set"
    openrouter_key = "✅ Configured" if config.openrouter_api_key else "❌ Not set"
    
    panel_content.append(f"OpenAI API Key: {openai_key}\n", style="cyan")
    panel_content.append(f"Anthropic API Key: {anthropic_key}\n", style="cyan")
    panel_content.append(f"OpenRouter API Key: {openrouter_key}\n", style="cyan")
    
    # Config file location
    config_path = Path.home() / ".codexarc"
    config_exists = "✅ Exists" if config_path.exists() else "❌ Not found"
    panel_content.append(f"\nConfig file (~/.codexarc): {config_exists}\n", style="magenta")
    
    console.print(Panel(panel_content, title="Codexa Configuration", border_style="blue"))
    
    if not config.has_valid_config():
        console.print("\n[yellow]⚠️  No API keys configured![/yellow]")
        show_setup_instructions()


@app.command()
def setup() -> None:
    """Set up Codexa configuration."""
    config = Config()
    
    console.print("[bold cyan]Codexa Setup[/bold cyan]\n")
    
    # Create default config file
    config.create_default_config()
    console.print("✅ Created default config file at ~/.codexarc")
    
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Get an API key from one of these providers:")
    console.print("   • OpenAI: https://platform.openai.com/api-keys")
    console.print("   • Anthropic: https://console.anthropic.com/")
    console.print("   • OpenRouter: https://openrouter.ai/keys")
    console.print("2. Set your API key as an environment variable:")
    console.print("   export OPENAI_API_KEY='your-key-here'")
    console.print("   export ANTHROPIC_API_KEY='your-key-here'")
    console.print("   export OPENROUTER_API_KEY='your-key-here'")
    console.print("3. Or create a .env file in your project directory")
    console.print("4. Run 'codexa config' to verify your setup")


def show_setup_instructions() -> None:
    """Show setup instructions for first-time users."""
    instructions = Text()
    instructions.append("🔧 Setup Required\n\n", style="bold yellow")
    instructions.append("Codexa needs an AI provider to work. Please:\n\n", style="white")
    instructions.append("1. Get an API key:\n", style="cyan")
    instructions.append("   • OpenAI: https://platform.openai.com/api-keys\n", style="dim")
    instructions.append("   • Anthropic: https://console.anthropic.com/\n", style="dim")
    instructions.append("   • OpenRouter: https://openrouter.ai/keys\n\n", style="dim")
    instructions.append("2. Set your API key:\n", style="cyan")
    instructions.append("   export OPENAI_API_KEY='your-key-here'\n", style="dim")
    instructions.append("   # or\n", style="dim")
    instructions.append("   export ANTHROPIC_API_KEY='your-key-here'\n", style="dim")
    instructions.append("   # or\n", style="dim")
    instructions.append("   export OPENROUTER_API_KEY='your-key-here'\n\n", style="dim")
    instructions.append("3. Run setup:\n", style="cyan")
    instructions.append("   codexa setup\n\n", style="dim")
    instructions.append("4. Start coding:\n", style="cyan")
    instructions.append("   codexa\n", style="dim")
    
    console.print(Panel(instructions, title="Welcome to Codexa!", border_style="yellow"))


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()