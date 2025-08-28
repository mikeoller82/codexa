"""
Interactive startup experience for Codexa with provider selection and onboarding.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.align import Align

from ..display.ascii_art import ASCIIArtRenderer, LogoTheme
from ..display.animations import AnimationEngine
from ..enhanced_config import EnhancedConfig


class StartupFlow(Enum):
    """Startup flow options."""
    FIRST_TIME = "first_time"
    QUICK_START = "quick_start"  
    INTERACTIVE = "interactive"
    SILENT = "silent"


@dataclass
class StartupChoice:
    """User choice during startup."""
    key: str
    display: str
    description: str
    value: Any
    default: bool = False


class InteractiveStartup:
    """Interactive startup experience manager."""
    
    def __init__(self, config: EnhancedConfig, console: Optional[Console] = None):
        self.config = config
        self.console = console or Console()
        self.ascii_renderer = ASCIIArtRenderer(self.console)
        self.animation_engine = AnimationEngine(self.console)
        
        # Startup state
        self.flow_type: Optional[StartupFlow] = None
        self.user_choices: Dict[str, Any] = {}
        self.first_run = not config.get_status()["config_file_exists"]
    
    async def run_startup_flow(self) -> Dict[str, Any]:
        """Run the complete startup flow."""
        try:
            # Determine flow type
            self.flow_type = await self._determine_flow_type()
            
            if self.flow_type == StartupFlow.SILENT:
                return await self._silent_startup()
            elif self.flow_type == StartupFlow.QUICK_START:
                return await self._quick_start()
            elif self.flow_type == StartupFlow.FIRST_TIME:
                return await self._first_time_setup()
            else:
                return await self._interactive_startup()
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Startup cancelled by user[/yellow]")
            return {"cancelled": True}
        except Exception as e:
            self.console.print(f"[red]Startup error: {e}[/red]")
            return {"error": str(e)}
    
    async def _determine_flow_type(self) -> StartupFlow:
        """Determine which startup flow to use."""
        # Check for first time setup
        if self.first_run:
            return StartupFlow.FIRST_TIME
        
        # Check user preferences
        startup_pref = self.config.user_config.get("startup", {}).get("flow", "interactive")
        
        if startup_pref == "silent":
            return StartupFlow.SILENT
        elif startup_pref == "quick":
            return StartupFlow.QUICK_START
        else:
            return StartupFlow.INTERACTIVE
    
    async def _silent_startup(self) -> Dict[str, Any]:
        """Silent startup with minimal output."""
        # Just show simple logo
        if self.config.is_feature_enabled("ascii_logo"):
            logo = self.ascii_renderer.render_logo(LogoTheme.MINIMAL, show_info=False)
            self.console.print(logo)
        
        return {"flow": "silent", "success": True}
    
    async def _quick_start(self) -> Dict[str, Any]:
        """Quick start with brief animation."""
        # Show animated logo
        if self.config.is_feature_enabled("ascii_logo"):
            animation = self.ascii_renderer.create_startup_animation()
            self.animation_engine.play_animation(animation, clear_screen=True)
        
        # Quick status check
        status = await self._check_system_status()
        if status.get("warnings"):
            self.console.print("[yellow]⚠ System warnings detected. Use 'interactive' mode for details.[/yellow]")
        
        return {"flow": "quick", "success": True, "status": status}
    
    async def _first_time_setup(self) -> Dict[str, Any]:
        """First time setup flow."""
        self.console.clear()
        
        # Welcome message
        welcome_panel = Panel(
            Align.center(
                Text.from_markup(
                    "[bold cyan]Welcome to Codexa![/bold cyan]\n\n"
                    "Let's get you set up with your AI-powered coding assistant.\n"
                    "This will only take a few minutes."
                )
            ),
            title="First Time Setup",
            border_style="cyan"
        )
        self.console.print(welcome_panel)
        
        # Logo theme selection
        await self._select_theme()
        
        # Provider setup
        await self._setup_providers()
        
        # MCP server setup
        await self._setup_mcp_servers()
        
        # Feature preferences
        await self._setup_features()
        
        # Show simple completion
        console.print("[green]✓ Setup complete![/green]")
        
        return {
            "flow": "first_time",
            "success": True,
            "choices": self.user_choices
        }
    
    async def _interactive_startup(self) -> Dict[str, Any]:
        """Interactive startup with user choices."""
        self.console.clear()
        
        # Show animated logo
        theme = LogoTheme(self.config.user_config.get("display", {}).get("theme", "default"))
        animation = self.ascii_renderer.create_startup_animation(theme)
        
        # Play animation in background while checking system
        animation_task = asyncio.create_task(self._play_startup_animation(animation))
        status_task = asyncio.create_task(self._check_system_status())
        
        # Wait for both to complete
        animation_result, status = await asyncio.gather(animation_task, status_task)
        
        # Show interactive menu if there are choices to make
        if await self._has_interactive_choices(status):
            await self._show_interactive_menu(status)
        
        return {
            "flow": "interactive", 
            "success": True,
            "status": status,
            "choices": self.user_choices
        }
    
    async def _select_theme(self):
        """Let user select ASCII art theme."""
        self.console.print("\n[bold yellow]Select Your Theme:[/bold yellow]")
        
        themes = [
            StartupChoice("default", "Default", "Clean, professional look", LogoTheme.DEFAULT, True),
            StartupChoice("minimal", "Minimal", "Simple and clean", LogoTheme.MINIMAL),
            StartupChoice("cyberpunk", "Cyberpunk", "Futuristic hacker aesthetic", LogoTheme.CYBERPUNK),
            StartupChoice("retro", "Retro", "80s computer vibes", LogoTheme.RETRO),
            StartupChoice("matrix", "Matrix", "Follow the white rabbit", LogoTheme.MATRIX)
        ]
        
        # Show theme previews
        for theme in themes:
            preview = self.ascii_renderer.render_logo(theme.value, show_info=False)
            panel = Panel(
                preview,
                title=f"{theme.display} - {theme.description}",
                border_style="dim"
            )
            self.console.print(panel)
        
        # Get user choice
        choices = [f"{i+1}. {theme.display}" for i, theme in enumerate(themes)]
        choice_text = "\n".join(choices)
        
        while True:
            try:
                choice_num = IntPrompt.ask(
                    f"\n{choice_text}\n\nSelect theme", 
                    default=1,
                    show_default=True
                )
                
                if 1 <= choice_num <= len(themes):
                    selected_theme = themes[choice_num - 1]
                    self.user_choices["theme"] = selected_theme.key
                    
                    # Show selected theme
                    self.console.clear()
                    logo = self.ascii_renderer.render_logo(selected_theme.value)
                    self.console.print(logo)
                    self.console.print(f"[green]✓ Selected theme: {selected_theme.display}[/green]")
                    break
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
            except (ValueError, KeyboardInterrupt):
                self.console.print("[red]Invalid choice. Please try again.[/red]")
    
    async def _setup_providers(self):
        """Setup AI providers."""
        self.console.print("\n[bold yellow]Configure AI Providers:[/bold yellow]")
        
        available_providers = self.config.get_available_providers()
        
        if not available_providers:
            self.console.print("[red]⚠ No AI providers available![/red]")
            self.console.print("Please set your API keys in environment variables:")
            self.console.print("• OPENAI_API_KEY for OpenAI")
            self.console.print("• ANTHROPIC_API_KEY for Anthropic")  
            self.console.print("• OPENROUTER_API_KEY for OpenRouter")
            
            if Confirm.ask("\nContinue anyway?", default=True):
                return
            else:
                raise KeyboardInterrupt()
        
        # Show available providers
        table = Table(title="Available AI Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Models", style="yellow")
        table.add_column("Status", style="green")
        
        for provider_name in available_providers:
            models = self.config.get_available_models(provider_name)
            status = "✓ Ready" if models else "⚠ No models"
            table.add_row(provider_name, f"{len(models)} available", status)
        
        self.console.print(table)
        
        # Select default provider
        if len(available_providers) > 1:
            current_provider = self.config.get_provider()
            provider_choices = list(enumerate(available_providers, 1))
            choice_text = "\n".join([f"{num}. {provider}" for num, provider in provider_choices])
            
            choice = IntPrompt.ask(
                f"\n{choice_text}\n\nSelect default provider",
                default=1,
                show_default=True
            )
            
            if 1 <= choice <= len(available_providers):
                selected_provider = available_providers[choice - 1]
                self.config.switch_provider(selected_provider)
                self.user_choices["provider"] = selected_provider
                self.console.print(f"[green]✓ Set default provider: {selected_provider}[/green]")
    
    async def _setup_mcp_servers(self):
        """Setup MCP servers."""
        self.console.print("\n[bold yellow]Configure MCP Servers:[/bold yellow]")
        
        mcp_servers = self.config.mcp_servers
        
        if not mcp_servers:
            self.console.print("[yellow]No MCP servers configured.[/yellow]")
            return
        
        # Show available MCP servers
        table = Table(title="Available MCP Servers")
        table.add_column("Server", style="cyan") 
        table.add_column("Capabilities", style="yellow")
        table.add_column("Enable?", style="green")
        
        for name, server_config in mcp_servers.items():
            capabilities_str = ", ".join(server_config.capabilities) or "General"
            enable_status = "Yes" if server_config.enabled else "No"
            table.add_row(name, capabilities_str, enable_status)
        
        self.console.print(table)
        
        # Ask about enabling servers
        if Confirm.ask("\nWould you like to enable MCP servers?", default=True):
            for name, server_config in mcp_servers.items():
                enable = Confirm.ask(f"Enable {name} ({', '.join(server_config.capabilities)})?", 
                                   default=server_config.enabled)
                if enable != server_config.enabled:
                    server_config.enabled = enable
                    self.user_choices[f"mcp_{name}"] = enable
                    
            self.console.print("[green]✓ MCP server preferences saved[/green]")
    
    async def _setup_features(self):
        """Setup feature preferences."""
        self.console.print("\n[bold yellow]Feature Preferences:[/bold yellow]")
        
        features = [
            ("ascii_logo", "ASCII art logos and animations", True),
            ("slash_commands", "Slash command system", True),
            ("provider_switching", "Runtime provider switching", True),
            ("mcp_integration", "MCP server integration", True)
        ]
        
        for feature_key, description, default in features:
            current = self.config.is_feature_enabled(feature_key)
            enable = Confirm.ask(f"Enable {description}?", default=current)
            
            if enable != current:
                self.config.enable_feature(feature_key, enable)
                self.user_choices[f"feature_{feature_key}"] = enable
        
        self.console.print("[green]✓ Feature preferences saved[/green]")
    
    async def _show_setup_complete(self):
        """Show setup completion message."""
        # This method is no longer called, replaced with simple message
    
    async def _play_startup_animation(self, animation) -> bool:
        """Play startup animation asynchronously."""
        try:
            # Convert sync animation to async
            await asyncio.sleep(0.1)  # Small delay for system check
            return True
        except Exception as e:
            self.console.print(f"[yellow]Animation error: {e}[/yellow]")
            return False
    
    async def _check_system_status(self) -> Dict[str, Any]:
        """Check system status asynchronously."""
        status = {
            "providers": len(self.config.get_available_providers()),
            "models": len(self.config.available_models),
            "mcp_servers": len([s for s in self.config.mcp_servers.values() if s.enabled]),
            "warnings": [],
            "errors": []
        }
        
        # Check for common issues
        if status["providers"] == 0:
            status["errors"].append("No AI providers available - set API keys")
        
        if status["mcp_servers"] == 0:
            status["warnings"].append("No MCP servers enabled - limited functionality")
        
        # Add a small delay to simulate checking
        await asyncio.sleep(0.5)
        
        return status
    
    async def _has_interactive_choices(self, status: Dict[str, Any]) -> bool:
        """Check if there are interactive choices to present."""
        # Show interactive menu if there are warnings or first run
        return len(status.get("warnings", [])) > 0 or len(status.get("errors", [])) > 0
    
    async def _show_interactive_menu(self, status: Dict[str, Any]):
        """Show interactive startup menu."""
        self.console.print("\n[bold yellow]Startup Options:[/bold yellow]")
        
        if status.get("errors"):
            self.console.print("[red]Errors found:[/red]")
            for error in status["errors"]:
                self.console.print(f"  ❌ {error}")
        
        if status.get("warnings"):
            self.console.print("[yellow]Warnings:[/yellow]")
            for warning in status["warnings"]:
                self.console.print(f"  ⚠ {warning}")
        
        # Offer choices
        choices = [
            "1. Continue anyway",
            "2. Quick setup",
            "3. Advanced configuration",
            "4. Exit"
        ]
        
        choice_text = "\n".join(choices)
        choice = IntPrompt.ask(f"\n{choice_text}\n\nSelect option", default=1)
        
        if choice == 2:
            await self._quick_setup()
        elif choice == 3:
            await self._advanced_configuration()
        elif choice == 4:
            raise KeyboardInterrupt()
        # Choice 1 (continue) just proceeds
    
    async def _quick_setup(self):
        """Quick setup flow."""
        self.console.print("\n[cyan]Running quick setup...[/cyan]")
        
        # Auto-configure based on available options
        available_providers = self.config.get_available_providers()
        if available_providers and not self.config.current_provider:
            self.config.switch_provider(available_providers[0])
            self.console.print(f"[green]✓ Set provider to {available_providers[0]}[/green]")
        
        # Enable basic MCP servers if available
        basic_servers = ["context7", "sequential"]
        for server_name in basic_servers:
            if server_name in self.config.mcp_servers:
                self.config.mcp_servers[server_name].enabled = True
                self.console.print(f"[green]✓ Enabled {server_name} MCP server[/green]")
    
    async def _advanced_configuration(self):
        """Advanced configuration options."""
        self.console.print("\n[cyan]Advanced Configuration[/cyan]")
        
        # Provider management
        if Confirm.ask("Configure AI providers?", default=True):
            await self._setup_providers()
        
        # MCP server management  
        if Confirm.ask("Configure MCP servers?", default=True):
            await self._setup_mcp_servers()
        
        # Feature toggles
        if Confirm.ask("Configure features?", default=False):
            await self._setup_features()
    
    def get_startup_summary(self) -> Dict[str, Any]:
        """Get summary of startup choices."""
        return {
            "flow_type": self.flow_type.value if self.flow_type else None,
            "first_run": self.first_run,
            "user_choices": self.user_choices,
            "config_status": self.config.get_status()
        }