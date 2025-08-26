"""
Interactive provider and model selection components for Codexa.
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Confirm, IntPrompt
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns


@dataclass
class ProviderInfo:
    """Information about an AI provider."""
    name: str
    display_name: str
    status: str
    models: List[str]
    capabilities: List[str]
    priority: int = 0


@dataclass
class ModelInfo:
    """Information about an AI model."""
    name: str
    display_name: str
    provider: str
    capabilities: List[str]
    context_length: int = 0
    cost_tier: str = "unknown"


class ProviderSelector:
    """Interactive provider selection interface."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def select_provider(self, providers: List[ProviderInfo], 
                       current_provider: Optional[str] = None) -> Optional[ProviderInfo]:
        """Interactively select an AI provider."""
        if not providers:
            self.console.print("[red]No providers available[/red]")
            return None
        
        if len(providers) == 1:
            return providers[0]
        
        # Show provider table
        self._display_provider_table(providers, current_provider)
        
        # Get user selection
        try:
            choices = list(range(1, len(providers) + 1))
            current_index = 1
            
            if current_provider:
                for i, provider in enumerate(providers):
                    if provider.name == current_provider:
                        current_index = i + 1
                        break
            
            choice = IntPrompt.ask(
                f"Select provider [1-{len(providers)}]",
                default=current_index,
                show_default=True
            )
            
            if 1 <= choice <= len(providers):
                return providers[choice - 1]
            else:
                self.console.print("[red]Invalid selection[/red]")
                return None
                
        except (KeyboardInterrupt, EOFError):
            return None
    
    def _display_provider_table(self, providers: List[ProviderInfo], 
                               current_provider: Optional[str] = None):
        """Display provider comparison table."""
        table = Table(title="Available AI Providers")
        table.add_column("Choice", style="cyan", width=6)
        table.add_column("Provider", style="bold")
        table.add_column("Status", style="green")
        table.add_column("Models", style="yellow")
        table.add_column("Capabilities", style="blue")
        
        for i, provider in enumerate(providers, 1):
            # Mark current provider
            name = provider.display_name
            if provider.name == current_provider:
                name = f"[bold green]{name} (current)[/bold green]"
            
            # Format model count
            model_count = f"{len(provider.models)} available"
            
            # Format capabilities
            capabilities = ", ".join(provider.capabilities[:3])
            if len(provider.capabilities) > 3:
                capabilities += f" (+{len(provider.capabilities) - 3} more)"
            
            table.add_row(
                str(i),
                name,
                provider.status,
                model_count,
                capabilities
            )
        
        self.console.print(table)
    
    def confirm_provider_switch(self, old_provider: str, 
                               new_provider: str) -> bool:
        """Confirm provider switch."""
        message = f"Switch from [blue]{old_provider}[/blue] to [green]{new_provider}[/green]?"
        return Confirm.ask(message, default=True)
    
    def show_provider_details(self, provider: ProviderInfo):
        """Show detailed provider information."""
        content = Text()
        content.append(f"Provider: {provider.display_name}\n\n", style="bold cyan")
        content.append(f"Status: {provider.status}\n", style="green")
        content.append(f"Models: {len(provider.models)} available\n", style="yellow")
        content.append(f"Capabilities: {', '.join(provider.capabilities)}\n", style="blue")
        
        if provider.models:
            content.append("\nAvailable Models:\n", style="bold")
            for model in provider.models[:5]:  # Show first 5 models
                content.append(f"• {model}\n", style="dim")
            if len(provider.models) > 5:
                content.append(f"... and {len(provider.models) - 5} more\n", style="dim")
        
        panel = Panel(content, title="Provider Details", border_style="cyan")
        self.console.print(panel)


class ModelSelector:
    """Interactive model selection interface."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def select_model(self, models: List[ModelInfo],
                    provider_name: Optional[str] = None,
                    current_model: Optional[str] = None) -> Optional[ModelInfo]:
        """Interactively select a model."""
        if not models:
            self.console.print("[red]No models available[/red]")
            return None
        
        if len(models) == 1:
            return models[0]
        
        # Filter by provider if specified
        if provider_name:
            models = [m for m in models if m.provider == provider_name]
            if not models:
                self.console.print(f"[red]No models available for provider {provider_name}[/red]")
                return None
        
        # Show model table
        self._display_model_table(models, current_model)
        
        # Get user selection
        try:
            current_index = 1
            
            if current_model:
                for i, model in enumerate(models):
                    if model.name == current_model:
                        current_index = i + 1
                        break
            
            choice = IntPrompt.ask(
                f"Select model [1-{len(models)}]",
                default=current_index,
                show_default=True
            )
            
            if 1 <= choice <= len(models):
                return models[choice - 1]
            else:
                self.console.print("[red]Invalid selection[/red]")
                return None
                
        except (KeyboardInterrupt, EOFError):
            return None
    
    def _display_model_table(self, models: List[ModelInfo],
                            current_model: Optional[str] = None):
        """Display model comparison table."""
        table = Table(title="Available Models")
        table.add_column("Choice", style="cyan", width=6)
        table.add_column("Model", style="bold")
        table.add_column("Provider", style="blue")
        table.add_column("Context", style="yellow")
        table.add_column("Cost", style="green")
        table.add_column("Capabilities", style="magenta")
        
        for i, model in enumerate(models, 1):
            # Mark current model
            name = model.display_name
            if model.name == current_model:
                name = f"[bold green]{name} (current)[/bold green]"
            
            # Format context length
            context = f"{model.context_length:,}" if model.context_length > 0 else "Unknown"
            
            # Format capabilities
            capabilities = ", ".join(model.capabilities[:2])
            if len(model.capabilities) > 2:
                capabilities += f" (+{len(model.capabilities) - 2})"
            
            table.add_row(
                str(i),
                name,
                model.provider,
                context,
                model.cost_tier,
                capabilities
            )
        
        self.console.print(table)
    
    def confirm_model_switch(self, old_model: str, new_model: str,
                            provider: Optional[str] = None) -> bool:
        """Confirm model switch."""
        old_display = f"{old_model}"
        new_display = f"{new_model}"
        
        if provider:
            new_display += f" ({provider})"
        
        message = f"Switch from [blue]{old_display}[/blue] to [green]{new_display}[/green]?"
        return Confirm.ask(message, default=True)
    
    def show_model_details(self, model: ModelInfo):
        """Show detailed model information."""
        content = Text()
        content.append(f"Model: {model.display_name}\n\n", style="bold cyan")
        content.append(f"Provider: {model.provider}\n", style="blue")
        content.append(f"Context Length: {model.context_length:,} tokens\n", style="yellow")
        content.append(f"Cost Tier: {model.cost_tier}\n", style="green")
        content.append(f"Capabilities: {', '.join(model.capabilities)}\n", style="magenta")
        
        panel = Panel(content, title="Model Details", border_style="cyan")
        self.console.print(panel)
    
    def show_model_comparison(self, models: List[ModelInfo]):
        """Show side-by-side model comparison."""
        if len(models) < 2:
            return
        
        comparison_table = Table(title="Model Comparison")
        comparison_table.add_column("Attribute", style="bold")
        
        for model in models[:3]:  # Compare up to 3 models
            comparison_table.add_column(model.display_name, style="cyan")
        
        # Add comparison rows
        comparison_table.add_row(
            "Provider",
            *[model.provider for model in models[:3]]
        )
        
        comparison_table.add_row(
            "Context Length",
            *[f"{model.context_length:,}" if model.context_length > 0 else "Unknown" 
              for model in models[:3]]
        )
        
        comparison_table.add_row(
            "Cost Tier",
            *[model.cost_tier for model in models[:3]]
        )
        
        # Show capabilities comparison
        all_capabilities = set()
        for model in models[:3]:
            all_capabilities.update(model.capabilities)
        
        for capability in sorted(all_capabilities):
            comparison_table.add_row(
                capability,
                *["✓" if capability in model.capabilities else "✗" 
                  for model in models[:3]]
            )
        
        self.console.print(comparison_table)


def create_provider_info_from_config(provider_name: str, 
                                    config: Dict[str, Any]) -> ProviderInfo:
    """Create ProviderInfo from configuration."""
    return ProviderInfo(
        name=provider_name,
        display_name=config.get("display_name", provider_name.title()),
        status=config.get("status", "Available"),
        models=config.get("models", []),
        capabilities=config.get("capabilities", []),
        priority=config.get("priority", 0)
    )


def create_model_info_from_config(model_name: str, provider: str,
                                 config: Dict[str, Any]) -> ModelInfo:
    """Create ModelInfo from configuration."""
    return ModelInfo(
        name=model_name,
        display_name=config.get("display_name", model_name),
        provider=provider,
        capabilities=config.get("capabilities", []),
        context_length=config.get("context_length", 0),
        cost_tier=config.get("cost_tier", "unknown")
    )