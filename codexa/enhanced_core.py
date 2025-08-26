"""
Enhanced Codexa agent with Phase 3 integrations including error handling, 
user guidance, and comprehensive UX enhancements.
"""

import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.markdown import Markdown

# Enhanced imports - Phase 2
from .enhanced_config import EnhancedConfig
from .enhanced_providers import EnhancedProviderFactory
from .mcp_service import MCPService
from .commands.command_registry import CommandRegistry
from .commands.command_executor import CommandExecutor
from .commands.built_in_commands import BuiltInCommands
from .display.animations import StartupAnimation
from .display.ascii_art import LogoTheme

# Phase 3 imports - Error handling and UX (with fallbacks)
try:
    from .error_handling import ErrorManager, ErrorContext, UserGuidanceSystem
except ImportError:
    # Fallback classes
    class ErrorManager:
        def __init__(self, console): self.console = console
        def handle_error(self, e, context, auto_recover=False): self.console.print(f"Error: {e}")
        def error_context(self, **kwargs): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get_error_statistics(self): return {}
    class ErrorContext: 
        def __init__(self, **kwargs): pass
    class UserGuidanceSystem:
        def __init__(self, console): self.console = console
        def provide_guidance(self, topic, context=None): pass

try:
    from .ui.interactive_startup import InteractiveStartup
except ImportError:
    class InteractiveStartup:
        def __init__(self, config, console): 
            self.config = config
            self.console = console
        async def run_startup_flow(self): 
            return {"flow": "basic", "success": True}

try:
    from .ui.contextual_help import ContextualHelpSystem as ContextualHelp
except ImportError:
    class ContextualHelp:
        def __init__(self, console): self.console = console
        async def show_main_help(self, **kwargs): 
            self.console.print("Type /help for commands")

from .ux.suggestion_engine import SuggestionEngine

from .mcp.advanced_health_monitor import AdvancedHealthMonitor
from .plugins.plugin_manager import PluginManager

# Legacy imports for compatibility
from .planning import PlanningManager
from .execution import TaskExecutionManager
from .codegen import CodeGenerator

console = Console()


class EnhancedCodexaAgent:
    """Enhanced Codexa agent with Phase 3 capabilities including comprehensive 
    error handling, user guidance, and advanced UX features."""

    def __init__(self):
        """Initialize the enhanced Codexa agent with Phase 3 features."""
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("codexa")
        
        # Core configuration
        self.config = EnhancedConfig()
        
        # Phase 3: Error handling and user guidance
        self.error_manager = ErrorManager(console)
        self.user_guidance = UserGuidanceSystem(console)
        
        # Enhanced provider system with error handling
        try:
            self.provider_factory = EnhancedProviderFactory(self.config)
            self.provider = self.provider_factory.get_provider()
            
            if not self.provider:
                raise Exception("No AI provider available. Please configure your API keys.")
        except Exception as e:
            context = ErrorContext(
                operation="provider_initialization",
                component="provider_factory",
                user_action="agent_startup"
            )
            self.error_manager.handle_error(e, context)
            raise
        
        # Project paths
        self.cwd = Path.cwd()
        self.codexa_dir = self.cwd / ".codexa"
        self.history: List[Dict] = []
        
        # Phase 3: Plugin system
        self.plugin_manager = PluginManager()
        
        # MCP service with advanced health monitoring
        self.mcp_service = None
        self.mcp_health_monitor = None
        if self.config.is_feature_enabled("mcp_integration"):
            self.mcp_service = MCPService(self.config)
            # Initialize health monitor with connection manager from MCP service
            if hasattr(self.mcp_service, 'connection_manager') and self.mcp_service.connection_manager:
                self.mcp_health_monitor = AdvancedHealthMonitor(self.mcp_service.connection_manager)
        
        # Command system
        self.command_registry = CommandRegistry()
        self.command_executor = CommandExecutor(self.command_registry, console)
        
        # Register built-in commands
        BuiltInCommands.register_all(self.command_registry)
        
        # Phase 3: Enhanced UX components
        self.interactive_startup = InteractiveStartup(self.config, console)
        self.contextual_help = ContextualHelp(self.command_registry, console)
        self.suggestion_engine = SuggestionEngine(console)
        
        # Display system
        self.startup_animation = StartupAnimation(console)
        
        # Legacy managers for compatibility
        self.planning_manager = PlanningManager(self.codexa_dir, self.provider)
        self.execution_manager = TaskExecutionManager(self.codexa_dir, self.provider)
        self.code_generator = CodeGenerator(self.cwd, self.provider)
        
        self.logger.info("Enhanced Codexa agent initialized with Phase 3 features")

    async def start_session(self) -> None:
        """Start an enhanced interactive Codexa session with Phase 3 features."""
        try:
            # Initialize project if needed
            self.initialize_project()
            
            # Phase 3: Run interactive startup flow
            startup_result = await self.interactive_startup.run_startup_flow()
            if startup_result.get("cancelled"):
                console.print("[yellow]Startup cancelled by user[/yellow]")
                return
            
            # Start MCP service if enabled
            if self.mcp_service:
                await self.mcp_service.start()
                
                # Start advanced health monitoring
                if self.mcp_health_monitor:
                    await self.mcp_health_monitor.start_monitoring()
            
            # Initialize plugins
            await self.plugin_manager.initialize_plugins()
            
            # Show contextual suggestions for first-time users
            if startup_result.get("flow") == "first_time":
                await self._show_getting_started_suggestions()
            
            # Main interaction loop with error handling
            await self._enhanced_main_loop()
            
        except Exception as e:
            context = ErrorContext(
                operation="session_startup",
                component="enhanced_core",
                user_action="start_session"
            )
            self.error_manager.handle_error(e, context)
            raise
        finally:
            # Cleanup
            await self._cleanup_session()

    async def _show_getting_started_suggestions(self):
        """Show getting started suggestions for new users."""
        suggestions = self.suggestion_engine.generate_suggestions({
            "session_count": 1,
            "mcp_servers_enabled": len([s for s in self.config.mcp_servers.values() if s.enabled]) if self.config.mcp_servers else 0,
            "project_files": [f.name for f in self.cwd.iterdir() if f.is_file()]
        })
        
        if suggestions:
            self.suggestion_engine.display_suggestions(suggestions, "🚀 Getting Started")

    async def _enhanced_main_loop(self):
        """Enhanced main interaction loop with contextual help and error handling."""
        while True:
            try:
                # Show contextual help if user types 'help' or '?'
                user_input = Prompt.ask("\n[bold cyan]codexa>[/bold cyan]").strip()
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n[yellow]Goodbye! Happy coding! 🚀[/yellow]")
                    break
                
                if not user_input:
                    continue
                
                # Show contextual help for common help requests
                if user_input.lower() in ["help", "?", "commands"]:
                    await self._show_contextual_help()
                    continue
                
                # Record user action for suggestion engine
                self.suggestion_engine.record_user_action(
                    user_input, 
                    context={
                        "timestamp": datetime.now().isoformat(),
                        "session_state": self._get_session_state()
                    }
                )
                
                # Handle commands vs natural language with error handling
                if user_input.startswith("/"):
                    await self._handle_slash_command_with_error_handling(user_input)
                else:
                    await self._handle_natural_language_with_error_handling(user_input)
                
                # Show contextual suggestions after successful interactions
                await self._show_contextual_suggestions(user_input)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                context = ErrorContext(
                    operation="main_loop_iteration",
                    component="enhanced_core",
                    user_action=user_input if 'user_input' in locals() else "unknown"
                )
                self.error_manager.handle_error(e, context, auto_recover=True)

    async def _show_contextual_help(self):
        """Show contextual help using the contextual help system."""
        await self.contextual_help.show_main_help(
            current_context=self._get_session_state(),
            available_commands=self.command_registry.get_command_names(),
            mcp_servers=self.mcp_service.get_available_servers() if self.mcp_service else []
        )

    async def _handle_slash_command_with_error_handling(self, command_input: str):
        """Handle slash command input with comprehensive error handling."""
        try:
            with self.error_manager.error_context(
                operation="slash_command_execution",
                component="command_executor",
                user_action=command_input
            ):
                if not self.config.is_feature_enabled("slash_commands"):
                    console.print("[yellow]Slash commands are disabled[/yellow]")
                    return
                
                # Execute command
                result = await self.command_executor.execute(
                    command_input, 
                    codexa_agent=self,
                    mcp_service=self.mcp_service,
                    config=self.config
                )
                
                # Display result
                if result.success:
                    if result.output:
                        console.print(result.output)
                else:
                    console.print(f"[red]Command failed: {result.error}[/red]")
                    
                    # Provide contextual guidance for command failures
                    command_name = command_input.split()[0] if command_input else "unknown"
                    self.user_guidance.provide_guidance(
                        f"command_failure_{command_name}",
                        context={"error": result.error, "command": command_input}
                    )
                
        except Exception as e:
            console.print(f"[red]Command execution failed: {e}[/red]")

    async def _handle_natural_language_with_error_handling(self, request: str):
        """Handle natural language input with comprehensive error handling."""
        console.print(f"\n[dim]Processing request...[/dim]")
        
        try:
            with self.error_manager.error_context(
                operation="natural_language_processing",
                component="enhanced_core",
                user_action=request
            ):
                # Get project context
                context = self._get_project_context()
                
                # Check for MCP-enhanced capabilities
                enhanced_response = await self._try_mcp_enhancement(request, context)
                if enhanced_response:
                    console.print("\n[bold green]Codexa:[/bold green]")
                    console.print(Markdown(enhanced_response))
                    return
                
                # Try planning workflow first
                if self.planning_manager.handle_request(request, context):
                    return
                
                # Check if this is a code generation request
                if self._is_code_generation_request(request):
                    await self._handle_code_generation_request_with_error_handling(request, context)
                else:
                    # Handle as regular natural language request with enhanced provider
                    response = await self.provider.ask(
                        prompt=request,
                        history=self.history,
                        context=context
                    )
                    
                    # Display response
                    console.print("\n[bold green]Codexa:[/bold green]")
                    console.print(Markdown(response))
                    
                    # Save to history
                    from datetime import datetime
                    self.history.append({
                        "user": request,
                        "assistant": response,
                        "timestamp": datetime.now().isoformat()
                    })
                
        except Exception as e:
            console.print(f"[red]Request processing failed: {e}[/red]")
            
            # Provide contextual guidance for processing failures
            self.user_guidance.provide_guidance(
                "processing_failure",
                context={"error": str(e), "request": request}
            )

    async def _handle_code_generation_request_with_error_handling(self, request: str, context: str):
        """Handle code generation request with enhanced error handling."""
        console.print("\n[cyan]🔨 Detected code generation request...[/cyan]")
        
        try:
            with self.error_manager.error_context(
                operation="code_generation",
                component="code_generator",
                user_action=request
            ):
                # Try MCP enhancement first
                if self.mcp_service:
                    try:
                        # UI component generation
                        if any(keyword in request.lower() for keyword in ["component", "ui", "interface"]):
                            result = await self.mcp_service.generate_ui_component(request)
                            if result:
                                console.print(f"[green]✅ Enhanced UI component generated![/green]")
                                console.print(f"[bold green]MCP Result:[/bold green]")
                                console.print(Markdown(f"```jsx\n{result.get('component', 'No component code')}\n```"))
                                return
                    except Exception as e:
                        self.logger.debug(f"MCP code generation failed: {e}")
                
                # Fallback to legacy code generation
                file_path, description = self._parse_code_generation_request(request)
                
                if file_path:
                    # Generate specific file
                    if self.code_generator.generate_and_create_file(file_path, description, context):
                        console.print(f"[green]✅ Successfully created {file_path}![/green]")
                        
                        # Show file suggestions for next steps
                        suggestions = self.code_generator.suggest_next_files(description, context)
                        if suggestions:
                            console.print("\n[yellow]💡 Suggested next files:[/yellow]")
                            for suggestion in suggestions[:3]:
                                priority_color = {"high": "red", "medium": "yellow", "low": "dim"}
                                color = priority_color.get(suggestion['priority'], 'white')
                                console.print(f"[{color}]• {suggestion['path']}[/{color}] - {suggestion['description']}")
                    else:
                        console.print(f"[red]Failed to create {file_path}[/red]")
                else:
                    # General code assistance with enhanced provider
                    response = await self.provider.ask(
                        prompt=f"Code generation request: {request}\n\nProvide implementation guidance and code examples.\n\n{context}",
                        history=self.history,
                        context=context
                    )
                    
                    console.print("\n[bold green]Codexa:[/bold green]")
                    console.print(Markdown(response))
                
                # Save to history
                from datetime import datetime
                self.history.append({
                    "user": request,
                    "assistant": f"Enhanced code generation request for: {file_path or 'general assistance'}",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            console.print(f"[red]Code generation failed: {e}[/red]")
            
            # Provide contextual guidance for code generation failures
            self.user_guidance.provide_guidance(
                "code_generation_failure",
                context={"error": str(e), "request": request}
            )

    async def _show_contextual_suggestions(self, user_input: str):
        """Show contextual suggestions based on user input and session state."""
        # Generate contextual suggestions
        context = {
            "recent_commands": [user_input],
            "session_activity": len(self.history),
            "mcp_servers_enabled": len([s for s in self.config.mcp_servers.values() if s.enabled]) if self.config.mcp_servers else 0,
            "project_files": [f.name for f in self.cwd.iterdir() if f.is_file()]
        }
        
        suggestions = self.suggestion_engine.generate_suggestions(context)
        
        # Only show suggestions occasionally to avoid overwhelming the user
        import random
        if suggestions and random.random() < 0.3:  # 30% chance
            self.suggestion_engine.display_suggestions(suggestions[:3], "💡 Suggestions")

    def _get_session_state(self) -> Dict[str, Any]:
        """Get current session state for contextual help and suggestions."""
        return {
            "command_history": len(self.history),
            "current_provider": self.config.get_provider(),
            "current_model": self.config.get_model(),
            "mcp_servers": [name for name, config in self.config.mcp_servers.items() if config.enabled] if self.config.mcp_servers else [],
            "project_path": str(self.cwd),
            "features_enabled": {
                "mcp_integration": self.config.is_feature_enabled("mcp_integration"),
                "slash_commands": self.config.is_feature_enabled("slash_commands"),
                "ascii_logo": self.config.is_feature_enabled("ascii_logo"),
            }
        }

    async def _cleanup_session(self):
        """Clean up session resources with comprehensive error handling."""
        self.logger.info("Starting session cleanup...")
        
        try:
            # Stop MCP health monitoring
            if self.mcp_health_monitor:
                await self.mcp_health_monitor.stop_monitoring()
            
            # Stop MCP service
            if self.mcp_service:
                await self.mcp_service.stop()
            
            # Cleanup plugins
            await self.plugin_manager.cleanup_plugins()
            
            # Save configuration
            try:
                self.config.save_config()
            except Exception as e:
                self.logger.error(f"Failed to save config: {e}")
            
            # Show session analytics
            self._show_session_analytics()
            
        except Exception as e:
            self.logger.error(f"Error during session cleanup: {e}")
        
        self.logger.info("Session cleanup complete")

    def _show_session_analytics(self):
        """Show session analytics including error statistics and suggestions."""
        try:
            # Error statistics
            error_stats = self.error_manager.get_error_statistics()
            if error_stats.get("total_errors", 0) > 0:
                console.print(f"\n[dim]Session Summary: {error_stats['total_errors']} errors encountered[/dim]")
            
            # Suggestion analytics
            suggestion_analytics = self.suggestion_engine.get_suggestion_analytics()
            if suggestion_analytics.get("total_actions", 0) > 0:
                console.print(f"[dim]Actions performed: {suggestion_analytics['total_actions']}[/dim]")
            
        except Exception as e:
            self.logger.debug(f"Failed to show session analytics: {e}")

    async def _show_startup_animation(self):
        """Show enhanced startup animation."""
        if not self.config.is_feature_enabled("ascii_logo"):
            return
        
        # Get theme from config
        theme_name = self.config.user_config.get("display", {}).get("theme", "default")
        try:
            theme = LogoTheme(theme_name.lower())
        except ValueError:
            theme = LogoTheme.DEFAULT
        
        # Configure animation
        interactive = self.config.user_config.get("display", {}).get("animations", True)
        self.startup_animation.configure(interactive=interactive)
        
        # Run startup sequence
        await self.startup_animation.run(theme=theme)

    async def _main_loop(self):
        """Enhanced main interaction loop."""
        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]codexa>[/bold cyan]").strip()
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n[yellow]Goodbye! Happy coding! 🚀[/yellow]")
                    break
                
                if not user_input:
                    continue
                
                # Handle commands vs natural language
                if user_input.startswith("/"):
                    await self._handle_slash_command(user_input)
                else:
                    await self._handle_natural_language(user_input)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                self.logger.error(f"Session error: {e}")

    async def _handle_slash_command(self, command_input: str):
        """Handle slash command input."""
        if not self.config.is_feature_enabled("slash_commands"):
            console.print("[yellow]Slash commands are disabled[/yellow]")
            return
        
        # Execute command
        result = await self.command_executor.execute(
            command_input, 
            codexa_agent=self,
            mcp_service=self.mcp_service,
            config=self.config
        )
        
        # Display result
        if result.success:
            if result.output:
                console.print(result.output)
        else:
            console.print(f"[red]Command failed: {result.error}[/red]")

    async def _handle_natural_language(self, request: str):
        """Handle natural language input with enhanced capabilities."""
        console.print(f"\n[dim]Processing request...[/dim]")
        
        # Get project context
        context = self._get_project_context()
        
        # Check for MCP-enhanced capabilities
        enhanced_response = await self._try_mcp_enhancement(request, context)
        if enhanced_response:
            console.print("\n[bold green]Codexa:[/bold green]")
            console.print(Markdown(enhanced_response))
            return
        
        # Try planning workflow first
        if self.planning_manager.handle_request(request, context):
            return
        
        # Check if this is a code generation request
        if self._is_code_generation_request(request):
            self._handle_code_generation_request(request, context)
        else:
            # Handle as regular natural language request with enhanced provider
            response = await self.provider.ask(
                prompt=request,
                history=self.history,
                context=context
            )
            
            # Display response
            console.print("\n[bold green]Codexa:[/bold green]")
            console.print(Markdown(response))
            
            # Save to history
            self.history.append({
                "user": request,
                "assistant": response,
                "timestamp": datetime.now().isoformat()
            })

    async def _try_mcp_enhancement(self, request: str, context: str) -> Optional[str]:
        """Try to enhance response using MCP servers."""
        if not self.mcp_service or not self.mcp_service.is_running:
            return None
        
        try:
            # Check if request can benefit from MCP enhancement
            request_lower = request.lower()
            
            # Documentation requests
            if any(keyword in request_lower for keyword in ["documentation", "docs", "example", "how to"]):
                try:
                    result = await self.mcp_service.query_server(
                        request, 
                        required_capabilities=["documentation", "search"],
                        context={"type": "documentation", "request": request}
                    )
                    return f"**Enhanced with MCP Documentation Server:**\n\n{result}"
                except Exception as e:
                    self.logger.debug(f"MCP documentation query failed: {e}")
            
            # Code analysis requests
            if any(keyword in request_lower for keyword in ["analyze", "review", "explain", "debug"]):
                try:
                    result = await self.mcp_service.analyze_code(
                        code=context,
                        context=request
                    )
                    if isinstance(result, dict) and "analysis" in result:
                        return f"**Enhanced Code Analysis:**\n\n{result['analysis']}"
                except Exception as e:
                    self.logger.debug(f"MCP code analysis failed: {e}")
            
            # UI generation requests
            if any(keyword in request_lower for keyword in ["component", "ui", "interface", "form"]):
                try:
                    result = await self.mcp_service.generate_ui_component(
                        description=request
                    )
                    if isinstance(result, dict) and "component" in result:
                        return f"**Generated UI Component:**\n\n```jsx\n{result['component']}\n```"
                except Exception as e:
                    self.logger.debug(f"MCP UI generation failed: {e}")
        
        except Exception as e:
            self.logger.error(f"MCP enhancement error: {e}")
        
        return None

    def initialize_project(self) -> None:
        """Initialize enhanced Codexa in the current project."""
        # Create CODEXA.md if it doesn't exist
        codexa_md_path = self.cwd / "CODEXA.md"
        if not codexa_md_path.exists():
            self._create_enhanced_codexa_md()
        
        # Create .codexa directory
        self.codexa_dir.mkdir(exist_ok=True)
        
        # Create .gitignore entry for .codexa if .git exists
        if (self.cwd / ".git").exists():
            self._update_gitignore()
        
        # Initialize config file if needed
        if not self.config.get_status()["config_file_exists"]:
            self.config.create_default_config()
            console.print("[green]✅ Created default configuration file[/green]")

    def _create_enhanced_codexa_md(self) -> None:
        """Create enhanced CODEXA.md with Phase 2 features."""
        from datetime import datetime
        
        codexa_md_content = f"""# Codexa Guidelines

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Project: {self.cwd.name}

## Enhanced Features

### 🚀 Phase 2 Capabilities
- **MCP Integration**: Context7, Sequential, Magic server support
- **Slash Commands**: Advanced command system with /help, /status, /mcp
- **Provider Switching**: Runtime AI provider/model selection
- **Interactive Startup**: Animated ASCII art with multiple themes

### 📡 MCP Servers Available
- **Context7**: Documentation and code examples
- **Sequential**: Complex reasoning and analysis  
- **Magic**: UI component generation
- **Playwright**: Cross-browser testing (if configured)

### 🎯 Slash Commands
- `/help` - Show command help
- `/status` - System status
- `/provider switch <name>` - Change AI provider
- `/model switch <name>` - Change AI model
- `/mcp enable <server>` - Enable MCP server
- `/commands` - List all commands

## Role Definition
Codexa acts as a proactive AI coding assistant with enhanced capabilities:

### Coding Philosophy
- Write clean, readable, and maintainable code
- Follow established patterns and conventions
- Prioritize code quality and best practices
- Include comprehensive testing and documentation
- Consider scalability and performance implications

### Enhanced Development Approach  
- Leverage MCP servers for specialized tasks
- Use intelligent provider routing for optimal responses
- Break down complex tasks into manageable steps
- Create structured plans before implementation
- Provide clear task breakdowns with priorities
- Maintain project context and consistency

### Communication Style
- Be proactive in suggesting improvements
- Explain reasoning behind architectural decisions
- Provide multiple solution options when appropriate
- Ask clarifying questions to ensure requirements are clear
- Offer guidance on best practices and industry standards
- Use slash commands for system interactions

### Project Standards
- Code Style: Clean and consistent formatting
- Testing: Comprehensive unit and integration tests
- Documentation: Clear inline comments and README updates
- Version Control: Meaningful commit messages and PR descriptions
- Security: Follow security best practices for the technology stack

## Project Context
This project is located at: `{self.cwd}`

Codexa will adapt its assistance based on the detected technology stack and project structure.
Enhanced features require proper API keys and MCP server configurations.

---
*This file was automatically generated by Enhanced Codexa v1.1. Modify it to customize how Codexa behaves in this project.*"""

        codexa_md_path = self.cwd / "CODEXA.md"
        with open(codexa_md_path, "w", encoding="utf-8") as f:
            f.write(codexa_md_content)
        
        console.print(f"[green]✅ Created enhanced CODEXA.md with Phase 2 features[/green]")

    def _update_gitignore(self) -> None:
        """Add .codexa to .gitignore if it's not already there."""
        gitignore_path = self.cwd / ".gitignore"
        
        # Read existing .gitignore
        existing_content = ""
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
        
        # Check if .codexa is already ignored
        if ".codexa/" not in existing_content and ".codexa" not in existing_content:
            # Add .codexa to .gitignore
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Codexa working directory\n.codexa/\n")
            console.print("[dim]Added .codexa/ to .gitignore[/dim]")

    def _get_project_context(self) -> str:
        """Get enhanced context about the current project."""
        context_parts = []
        
        # Add CODEXA.md content
        codexa_md = self.cwd / "CODEXA.md"
        if codexa_md.exists():
            with open(codexa_md, "r", encoding="utf-8") as f:
                context_parts.append(f"Project Guidelines:\n{f.read()}")
        
        # Add basic project info
        context_parts.append(f"Current Directory: {self.cwd}")
        
        # Add enhanced system status
        if self.mcp_service:
            available_servers = self.mcp_service.get_available_servers()
            if available_servers:
                context_parts.append(f"Available MCP Servers: {', '.join(available_servers)}")
        
        # Add provider info
        current_provider = self.config.get_provider()
        current_model = self.config.get_model()
        context_parts.append(f"Current AI Provider: {current_provider} ({current_model})")
        
        # Add file listing (basic)
        files = []
        for item in self.cwd.iterdir():
            if not item.name.startswith('.') and item.is_file():
                files.append(item.name)
        
        if files:
            context_parts.append(f"Files in project: {', '.join(files[:10])}")
        
        return "\n\n".join(context_parts)

    def _is_code_generation_request(self, request: str) -> bool:
        """Check if the request is asking for code generation."""
        code_keywords = [
            "create", "generate", "write", "implement", "build",
            "add", "make", "code", "function", "class", "component",
            "file", "script", "module", "api", "endpoint", "route"
        ]
        
        file_extensions = [
            ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
            ".scss", ".json", ".yaml", ".yml", ".md", ".rs", ".go"
        ]
        
        request_lower = request.lower()
        
        # Check for code keywords
        has_code_keywords = any(keyword in request_lower for keyword in code_keywords)
        
        # Check for file extensions
        has_file_extensions = any(ext in request_lower for ext in file_extensions)
        
        # Check for specific code-related phrases
        code_phrases = [
            "write a", "create a", "generate a", "build a",
            "implement a", "add a", "make a", "file for",
            "component for", "function to", "class that"
        ]
        
        has_code_phrases = any(phrase in request_lower for phrase in code_phrases)
        
        return has_code_keywords or has_file_extensions or has_code_phrases

    def _handle_code_generation_request(self, request: str, context: str) -> None:
        """Handle a code generation request with MCP enhancement."""
        console.print("\n[cyan]🔨 Detected code generation request...[/cyan]")
        
        # Try MCP enhancement first
        if self.mcp_service:
            try:
                # UI component generation
                if any(keyword in request.lower() for keyword in ["component", "ui", "interface"]):
                    result = asyncio.run(self.mcp_service.generate_ui_component(request))
                    if result:
                        console.print(f"[green]✅ Enhanced UI component generated![/green]")
                        console.print(f"[bold green]MCP Result:[/bold green]")
                        console.print(Markdown(f"```jsx\n{result.get('component', 'No component code')}\n```"))
                        return
            except Exception as e:
                self.logger.debug(f"MCP code generation failed: {e}")
        
        # Fallback to legacy code generation
        file_path, description = self._parse_code_generation_request(request)
        
        if file_path:
            # Generate specific file
            if self.code_generator.generate_and_create_file(file_path, description, context):
                console.print(f"[green]✅ Successfully created {file_path}![/green]")
                
                # Show file suggestions for next steps
                suggestions = self.code_generator.suggest_next_files(description, context)
                if suggestions:
                    console.print("\n[yellow]💡 Suggested next files:[/yellow]")
                    for suggestion in suggestions[:3]:
                        priority_color = {"high": "red", "medium": "yellow", "low": "dim"}
                        color = priority_color.get(suggestion['priority'], 'white')
                        console.print(f"[{color}]• {suggestion['path']}[/{color}] - {suggestion['description']}")
            else:
                console.print(f"[red]Failed to create {file_path}[/red]")
        else:
            # General code assistance with enhanced provider
            response = asyncio.run(self.provider.ask(
                prompt=f"Code generation request: {request}\n\nProvide implementation guidance and code examples.\n\n{context}",
                history=self.history,
                context=context
            ))
            
            console.print("\n[bold green]Codexa:[/bold green]")
            console.print(Markdown(response))
        
        # Save to history
        self.history.append({
            "user": request,
            "assistant": f"Enhanced code generation request for: {file_path or 'general assistance'}",
            "timestamp": datetime.now().isoformat()
        })

    def _parse_code_generation_request(self, request: str):
        """Parse a code generation request (reused from original)."""
        import re
        from datetime import datetime
        
        # Look for explicit file paths
        file_pattern = r'([a-zA-Z0-9_/-]+\.[a-zA-Z0-9]+)'
        file_matches = re.findall(file_pattern, request)
        
        if file_matches:
            return file_matches[0], request
        
        # Try to infer file path from request
        request_lower = request.lower()
        
        # Common patterns
        if "component" in request_lower and ("react" in request_lower or "jsx" in request_lower):
            component_match = re.search(r'(\w+)\s*component', request_lower)
            if component_match:
                component_name = component_match.group(1).capitalize()
                return f"src/components/{component_name}.jsx", request
        
        if "api" in request_lower or "endpoint" in request_lower:
            if "python" in request_lower or "flask" in request_lower:
                return "app.py", request
            elif "javascript" in request_lower or "node" in request_lower:
                return "server.js", request
        
        if "style" in request_lower or "css" in request_lower:
            return "styles.css", request
        
        if "config" in request_lower:
            if "json" in request_lower:
                return "config.json", request
            elif "yaml" in request_lower:
                return "config.yaml", request
        
        return None, request

    async def shutdown(self):
        """Graceful shutdown of enhanced agent."""
        self.logger.info("Shutting down enhanced Codexa agent...")
        
        if self.mcp_service:
            await self.mcp_service.stop()
        
        # Save configuration
        try:
            self.config.save_config()
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
        
        self.logger.info("Shutdown complete")