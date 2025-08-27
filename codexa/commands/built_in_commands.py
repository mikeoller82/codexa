"""
Built-in commands for Codexa.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

from .command_registry import Command, CommandContext, CommandCategory, CommandParameter
from .command_executor import CommandExecutor


class HelpCommand(Command):
    """Display help information."""
    
    def __init__(self):
        super().__init__()
        self.name = "help"
        self.description = "Show help information for commands"
        self.category = CommandCategory.HELP
        self.parameters = [
            CommandParameter("command", str, False, None, "Specific command to get help for")
        ]
        self.aliases = ["h", "?"]
    
    async def execute(self, context: CommandContext) -> str:
        command_name = context.parsed_args.get("command")
        
        if command_name:
            # Help for specific command
            if hasattr(context.codexa_agent, 'command_executor'):
                help_text = context.codexa_agent.command_executor.get_command_help(command_name)
                return help_text
            return f"Help not available for '{command_name}'"
        else:
            # General help
            help_text = """
[bold cyan]Codexa Commands Help[/bold cyan]

[yellow]Usage:[/yellow] /command [arguments] [--flags]

[yellow]Examples:[/yellow]
• /help status          - Get help for status command
• /provider switch openai - Switch to OpenAI provider  
• /mcp enable context7   - Enable Context7 MCP server
• /model list           - List available models

[yellow]Categories:[/yellow]
• [cyan]/help[/cyan] - Show commands by category
• [cyan]/help core[/cyan] - Core system commands
• [cyan]/help mcp[/cyan] - MCP server commands
• [cyan]/help provider[/cyan] - Provider management

Type [cyan]/commands[/cyan] to see all available commands.
            """
            return help_text.strip()


class StatusCommand(Command):
    """Show system status."""
    
    def __init__(self):
        super().__init__()
        self.name = "status"
        self.description = "Show Codexa system status"
        self.category = CommandCategory.CORE
        self.parameters = [
            CommandParameter("detailed", bool, False, False, "Show detailed status information")
        ]
        self.aliases = ["stat"]
    
    async def execute(self, context: CommandContext) -> str:
        detailed = context.parsed_args.get("detailed", False)
        
        status_info = []
        
        # Basic system info
        status_info.append("[bold cyan]Codexa System Status[/bold cyan]\n")
        
        # Provider status
        if context.config:
            current_provider = context.config.get_provider()
            current_model = context.config.get_model()
            available_providers = context.config.get_available_providers()
            
            status_info.append(f"[yellow]Current Provider:[/yellow] {current_provider}")
            status_info.append(f"[yellow]Current Model:[/yellow] {current_model}")
            status_info.append(f"[yellow]Available Providers:[/yellow] {', '.join(available_providers)}")
        
        # MCP status
        if context.mcp_service:
            mcp_status = context.mcp_service.get_service_status()
            status_info.append(f"[yellow]MCP Service:[/yellow] {'Running' if mcp_status['running'] else 'Stopped'}")
            
            available_servers = mcp_status['connection_manager']['available_servers']
            status_info.append(f"[yellow]MCP Servers:[/yellow] {len(available_servers)} available")
            
            if detailed and available_servers:
                status_info.append(f"  - {', '.join(available_servers)}")
        
        # Command system status
        if hasattr(context.codexa_agent, 'command_registry'):
            registry = context.codexa_agent.command_registry
            stats = registry.get_stats()
            status_info.append(f"[yellow]Commands:[/yellow] {stats['enabled_commands']}/{stats['total_commands']} enabled")
        
        # Session info
        if hasattr(context.codexa_agent, 'history'):
            history_count = len(context.codexa_agent.history)
            status_info.append(f"[yellow]Session Messages:[/yellow] {history_count}")
        
        return "\n".join(status_info)


class ProviderCommand(Command):
    """Manage AI providers."""
    
    def __init__(self):
        super().__init__()
        self.name = "provider"
        self.description = "Manage AI providers and models"
        self.category = CommandCategory.PROVIDER
        self.parameters = [
            CommandParameter("action", str, True, None, "Action to perform", 
                           choices=["list", "switch", "status", "models"])
        ]
        self.aliases = ["prov"]
    
    async def execute(self, context: CommandContext) -> str:
        action = context.parsed_args.get("action")
        args = context.parsed_args.get("args", [])
        
        if not context.config:
            return "[red]Configuration not available[/red]"
        
        if action == "list":
            providers = context.config.get_available_providers()
            current = context.config.get_provider()
            
            result = ["[bold cyan]Available Providers:[/bold cyan]"]
            for provider in providers:
                marker = " [green]✓[/green]" if provider == current else ""
                result.append(f"• {provider}{marker}")
            
            return "\n".join(result)
        
        elif action == "switch":
            if not args:
                return "[red]Provider name required for switch action[/red]"
            
            provider_name = args[0]
            success = context.config.switch_provider(provider_name)
            
            if success:
                return f"[green]Switched to provider: {provider_name}[/green]"
            else:
                return f"[red]Failed to switch to provider: {provider_name}[/red]"
        
        elif action == "status":
            current_provider = context.config.get_provider()
            current_model = context.config.get_model()
            
            status = f"""[bold cyan]Provider Status:[/bold cyan]
[yellow]Current Provider:[/yellow] {current_provider}
[yellow]Current Model:[/yellow] {current_model}
[yellow]Available Providers:[/yellow] {len(context.config.get_available_providers())}"""
            
            return status
        
        elif action == "models":
            provider_name = args[0] if args else context.config.get_provider()
            models = context.config.get_available_models(provider_name)
            
            if models:
                result = [f"[bold cyan]Models for {provider_name}:[/bold cyan]"]
                current_model = context.config.get_model()
                
                for model in models:
                    marker = " [green]✓[/green]" if model == current_model else ""
                    result.append(f"• {model}{marker}")
                
                return "\n".join(result)
            else:
                return f"[red]No models available for provider: {provider_name}[/red]"
        
        return f"[red]Unknown provider action: {action}[/red]"


class ModelCommand(Command):
    """Manage AI models."""
    
    def __init__(self):
        super().__init__()
        self.name = "model"
        self.description = "Manage AI models with dynamic discovery"
        self.category = CommandCategory.PROVIDER
        self.parameters = [
            CommandParameter("action", str, True, None, "Action to perform",
                           choices=["list", "discover", "select", "switch", "info", "clear-cache"])
        ]
    
    async def execute(self, context: CommandContext) -> str:
        action = context.parsed_args.get("action")
        # Skip the first arg since it's mapped to the action parameter
        raw_args = context.parsed_args.get("args", [])
        args = raw_args[1:] if raw_args and len(raw_args) > 0 else []
        
        if not context.config:
            return "[red]Configuration not available[/red]"
        
        if action == "list":
            # Show configured models (legacy support)
            current_provider = context.config.get_provider()
            models = context.config.get_available_models(current_provider)
            current_model = context.config.get_model()
            
            result = [f"[bold cyan]Configured Models ({current_provider}):[/bold cyan]"]
            for model in models:
                marker = " [green]✓[/green]" if model == current_model else ""
                result.append(f"• {model}{marker}")
            
            result.append(f"\n[dim]Use `/model discover` to fetch models from provider APIs[/dim]")
            return "\n".join(result)
        
        elif action == "discover":
            # Dynamic model discovery from provider APIs
            from ..services.model_service import ModelService
            from rich.progress import Progress, SpinnerColumn, TextColumn
            from rich.console import Console
            
            console = Console()
            model_service = ModelService(context.config)
            
            provider_name = args[0] if args else None
            
            # Show progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                discovery_task = progress.add_task("Discovering available models...", total=None)
                
                if provider_name:
                    models_data = {
                        provider_name: model_service._discover_provider_models(provider_name)
                    }
                else:
                    models_data = model_service.discover_all_models()
                
                progress.remove_task(discovery_task)
            
            # Format results
            result = []
            total_models = 0
            
            for provider, discovery_result in models_data.items():
                if discovery_result.success:
                    models = discovery_result.models
                    total_models += len(models)
                    
                    result.append(f"[bold cyan]{provider}:[/bold cyan] {len(models)} models ({discovery_result.response_time:.2f}s)")
                    
                    # Show top 3 models
                    for i, model in enumerate(models[:3]):
                        result.append(f"  • {model.get('name', model.get('id', ''))}")
                    
                    if len(models) > 3:
                        result.append(f"  ... and {len(models) - 3} more")
                else:
                    result.append(f"[red]{provider}: Failed - {discovery_result.error}[/red]")
            
            result.insert(0, f"[bold green]Discovered {total_models} models total[/bold green]\n")
            result.append(f"\n[dim]Use `/model select` for interactive selection[/dim]")
            
            return "\n".join(result)
        
        elif action == "select":
            # Interactive model selection
            from ..services.model_service import ModelService, InteractiveModelSelector
            
            model_service = ModelService(context.config)
            selector = InteractiveModelSelector(model_service)
            
            provider_name = args[0] if args else None
            
            try:
                result = await selector.select_model_interactive(provider_name)
                if result:
                    provider, model_name = result
                    # Try to switch to selected model
                    if hasattr(context.config, 'switch_model'):
                        success = context.config.switch_model(model_name, provider)
                        if success:
                            return f"[green]Selected and switched to: {model_name} ({provider})[/green]"
                        else:
                            return f"[yellow]Selected {model_name} ({provider}) but failed to update config[/yellow]"
                    else:
                        return f"[yellow]Selected: {model_name} ({provider}) - Manual config update needed[/yellow]"
                else:
                    return "[yellow]No model selected[/yellow]"
            except Exception as e:
                return f"[red]Selection failed: {e}[/red]"
        
        elif action == "switch":
            if not args:
                return "[red]Model name required for switch action[/red]"
            
            model_name = args[0]
            provider = args[1] if len(args) > 1 else None
            
            if hasattr(context.config, 'switch_model'):
                success = context.config.switch_model(model_name, provider)
            else:
                # Fallback for basic config
                success = False
                if hasattr(context.config, 'user_config'):
                    try:
                        current_provider = provider or context.config.get_provider()
                        context.config.user_config.setdefault('models', {})[current_provider] = model_name
                        success = True
                    except Exception:
                        pass
            
            if success:
                return f"[green]Switched to model: {model_name}{f' ({provider})' if provider else ''}[/green]"
            else:
                return f"[red]Failed to switch to model: {model_name}[/red]"
        
        elif action == "info":
            model_name = args[0] if args else context.config.get_model()
            
            # Try enhanced config first
            if hasattr(context.config, 'get_model_config'):
                model_config = context.config.get_model_config(model_name)
                if model_config:
                    info = f"""[bold cyan]Model Information:[/bold cyan]
[yellow]Name:[/yellow] {model_config.name}
[yellow]Provider:[/yellow] {model_config.provider}
[yellow]Max Tokens:[/yellow] {model_config.max_tokens}
[yellow]Temperature:[/yellow] {model_config.temperature}
[yellow]Capabilities:[/yellow] {', '.join(model_config.capabilities) or 'None specified'}"""
                    return info
            
            # Fallback to basic info
            current_provider = context.config.get_provider()
            info = f"""[bold cyan]Model Information:[/bold cyan]
[yellow]Name:[/yellow] {model_name}
[yellow]Provider:[/yellow] {current_provider}
[yellow]Status:[/yellow] Currently configured"""
            
            return info
        
        elif action == "clear-cache":
            # Clear model discovery cache
            from ..services.model_service import ModelService
            
            model_service = ModelService(context.config)
            provider_name = args[0] if args else None
            
            model_service.clear_cache(provider_name)
            
            if provider_name:
                return f"[green]Cleared model cache for {provider_name}[/green]"
            else:
                return "[green]Cleared all model caches[/green]"
        
        return f"[red]Unknown model action: {action}[/red]"


class MCPCommand(Command):
    """Manage MCP servers."""
    
    def __init__(self):
        super().__init__()
        self.name = "mcp"
        self.description = "Manage MCP servers and capabilities"
        self.category = CommandCategory.MCP
        self.parameters = [
            CommandParameter("action", str, True, None, "Action to perform",
                           choices=["status", "list", "enable", "disable", "restart", "query"])
        ]
    
    async def execute(self, context: CommandContext) -> str:
        action = context.parsed_args.get("action")
        args = context.parsed_args.get("args", [])
        
        if not context.mcp_service:
            return "[red]MCP service not available[/red]"
        
        if action == "status":
            status = context.mcp_service.get_service_status()
            
            result = f"""[bold cyan]MCP Service Status:[/bold cyan]
[yellow]Running:[/yellow] {status['running']}
[yellow]Available Servers:[/yellow] {len(status['connection_manager']['available_servers'])}
[yellow]Total Servers:[/yellow] {status['connection_manager']['total_servers']}"""
            
            if status.get('uptime'):
                result += f"\n[yellow]Uptime:[/yellow] {status['uptime']}"
            
            return result
        
        elif action == "list":
            servers = context.mcp_service.get_available_servers()
            capabilities = context.mcp_service.get_server_capabilities()
            
            if not servers:
                return "[yellow]No MCP servers available[/yellow]"
            
            result = ["[bold cyan]Available MCP Servers:[/bold cyan]"]
            for server in servers:
                server_caps = capabilities.get(server, [])
                caps_str = f"({', '.join(server_caps)})" if server_caps else "(no capabilities)"
                result.append(f"• {server} {caps_str}")
            
            return "\n".join(result)
        
        elif action == "enable":
            if not args:
                return "[red]Server name required for enable action[/red]"
            
            server_name = args[0]
            success = context.mcp_service.enable_server(server_name)
            
            if success:
                return f"[green]Enabled MCP server: {server_name}[/green]"
            else:
                return f"[red]Failed to enable server: {server_name}[/red]"
        
        elif action == "disable":
            if not args:
                return "[red]Server name required for disable action[/red]"
            
            server_name = args[0]
            success = context.mcp_service.disable_server(server_name)
            
            if success:
                return f"[yellow]Disabled MCP server: {server_name}[/yellow]"
            else:
                return f"[red]Failed to disable server: {server_name}[/red]"
        
        elif action == "restart":
            if not args:
                return "[red]Server name required for restart action[/red]"
            
            server_name = args[0]
            success = await context.mcp_service.restart_server(server_name)
            
            if success:
                return f"[green]Restarted MCP server: {server_name}[/green]"
            else:
                return f"[red]Failed to restart server: {server_name}[/red]"
        
        elif action == "query":
            if len(args) < 2:
                return "[red]Server name and query required[/red]"
            
            server_name = args[0]
            query = " ".join(args[1:])
            
            try:
                result = await context.mcp_service.query_server(query, server_name)
                return f"[bold cyan]Response from {server_name}:[/bold cyan]\n{result}"
            except Exception as e:
                return f"[red]Query failed: {e}[/red]"
        
        return f"[red]Unknown MCP action: {action}[/red]"


class CommandsCommand(Command):
    """List available commands."""
    
    def __init__(self):
        super().__init__()
        self.name = "commands"
        self.description = "List all available commands"
        self.category = CommandCategory.HELP
        self.parameters = [
            CommandParameter("category", str, False, None, "Filter by category")
        ]
        self.aliases = ["cmds", "list"]
    
    async def execute(self, context: CommandContext) -> str:
        category = context.parsed_args.get("category")
        
        if hasattr(context.codexa_agent, 'command_executor'):
            executor = context.codexa_agent.command_executor
            
            # Use executor's display method if available
            if hasattr(executor, 'display_help_table'):
                console = Console()
                with console.capture() as capture:
                    executor.display_help_table(category)
                return capture.get()
        
        # Fallback to simple list
        if hasattr(context.codexa_agent, 'command_registry'):
            registry = context.codexa_agent.command_registry
            
            if category:
                from .command_registry import CommandCategory
                try:
                    cat_enum = CommandCategory(category.lower())
                    commands = registry.list_commands(cat_enum)
                except ValueError:
                    return f"[red]Unknown category: {category}[/red]"
            else:
                commands = registry.list_commands()
            
            result = ["[bold cyan]Available Commands:[/bold cyan]"]
            for cmd_name in commands:
                command = registry.commands[cmd_name]
                result.append(f"• [cyan]/{cmd_name}[/cyan] - {command.description}")
            
            return "\n".join(result)
        
        return "[red]Command registry not available[/red]"


class ConfigCommand(Command):
    """Manage configuration."""
    
    def __init__(self):
        super().__init__()
        self.name = "config"
        self.description = "Manage Codexa configuration"
        self.category = CommandCategory.CORE
        self.parameters = [
            CommandParameter("action", str, True, None, "Action to perform",
                           choices=["show", "set", "reset", "save"])
        ]
    
    async def execute(self, context: CommandContext) -> str:
        action = context.parsed_args.get("action")
        args = context.parsed_args.get("args", [])
        
        if not context.config:
            return "[red]Configuration not available[/red]"
        
        if action == "show":
            status = context.config.get_status()
            
            result = f"""[bold cyan]Configuration Status:[/bold cyan]
[yellow]Current Provider:[/yellow] {status['current_provider']}
[yellow]Current Model:[/yellow] {status['current_model']}
[yellow]Available Providers:[/yellow] {len(status['available_providers'])}
[yellow]Total Models:[/yellow] {status['total_models']}
[yellow]MCP Servers Enabled:[/yellow] {status['mcp_servers_enabled']}
[yellow]Config File:[/yellow] {'Exists' if status['config_file_exists'] else 'Missing'}"""
            
            return result
        
        elif action == "set":
            if len(args) < 2:
                return "[red]Key and value required for set action[/red]"
            
            key, value = args[0], args[1]
            
            # Handle boolean values
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            
            # Simple feature flag setting
            if key.startswith('feature.'):
                feature_name = key[8:]  # Remove 'feature.' prefix
                context.config.enable_feature(feature_name, value)
                return f"[green]Set {key} = {value}[/green]"
            
            return f"[red]Configuration key '{key}' not supported[/red]"
        
        elif action == "save":
            try:
                context.config.save_config()
                return "[green]Configuration saved successfully[/green]"
            except Exception as e:
                return f"[red]Failed to save configuration: {e}[/red]"
        
        elif action == "reset":
            try:
                context.config.create_default_config()
                return "[yellow]Configuration reset to defaults[/yellow]"
            except Exception as e:
                return f"[red]Failed to reset configuration: {e}[/red]"
        
        return f"[red]Unknown config action: {action}[/red]"


class BuiltInCommands:
    """Registry of built-in Codexa commands."""
    
    @staticmethod
    def register_all(registry):
        """Register all built-in commands."""
        commands = [
            HelpCommand(),
            StatusCommand(),
            ProviderCommand(),
            ModelCommand(), 
            MCPCommand(),
            CommandsCommand(),
            ConfigCommand()
        ]
        
        for command in commands:
            registry.register(command)
        
        return len(commands)