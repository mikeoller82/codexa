"""
Enhanced Codexa agent with tool-based architecture.
Complete restructure from hardcoded functionality to dynamic tool system.
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

# Tool-based architecture imports
from .tools.base.tool_manager import ToolManager
from .tools.base.tool_registry import ToolRegistry  
from .tools.base.tool_interface import ToolContext

# Configuration and providers
from .enhanced_config import EnhancedConfig
from .enhanced_providers import EnhancedProviderFactory
from .mcp_service import MCPService

console = Console()


class EnhancedCodexaAgent:
    """Enhanced Codexa agent with dynamic tool-based architecture."""

    def __init__(self):
        """Initialize the enhanced Codexa agent with tool-based architecture."""
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("codexa")
        
        # Core configuration
        self.config = EnhancedConfig()
        
        # Enhanced provider system
        try:
            self.provider_factory = EnhancedProviderFactory(self.config)
            self.provider = self.provider_factory.get_provider()
            
            if not self.provider:
                raise Exception("No AI provider available. Please configure your API keys.")
        except Exception as e:
            console.print(f"[red]Provider initialization failed: {e}[/red]")
            raise
        
        # Project paths
        self.cwd = Path.cwd()
        self.codexa_dir = self.cwd / ".codexa"
        self.history: List[Dict] = []
        
        # MCP service
        self.mcp_service = None
        if self.config.is_feature_enabled("mcp_integration"):
            try:
                self.mcp_service = MCPService(self.config)
                self.logger.info("MCP service initialized")
            except Exception as e:
                self.logger.warning(f"MCP service initialization failed: {e}")
        
        # Tool-based architecture - the heart of the new system
        self.tool_registry = ToolRegistry()
        self.tool_manager = ToolManager(enable_performance_monitoring=True)
        
        # Initialize tools
        self._initialize_tools()
        
        self.logger.info("Enhanced Codexa agent initialized with tool-based architecture")
    
    def _initialize_tools(self):
        """Initialize and register all available tools."""
        self.logger.info("Discovering and registering tools...")
        
        # Discover tools automatically from the tools directory
        discovered_count = self.tool_registry.discover_tools()
        available_tools = self.tool_registry.get_all_tools()
        self.logger.info(f"Discovered {discovered_count} tools: {list(available_tools.keys())}")
        
        # Log tool categories
        categories = {}
        for tool_name, tool_info in available_tools.items():
            category = tool_info.category if hasattr(tool_info, 'category') else 'unknown'
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)
        
        for category, tools in categories.items():
            self.logger.info(f"  {category.title()}: {', '.join(tools)}")

    async def start_session(self) -> None:
        """Start an enhanced interactive Codexa session with tool-based architecture."""
        try:
            # Initialize project if needed
            self.initialize_project()
            
            # Show startup animation using animation tool
            await self._show_startup_with_tools()
            
            # Start MCP service if enabled
            if self.mcp_service:
                await self.mcp_service.start()
                self.logger.info("MCP service started")
            
            # Main interaction loop with tool-based processing
            await self._main_loop()
            
        except Exception as e:
            console.print(f"[red]Session startup failed: {e}[/red]")
            raise
        finally:
            # Cleanup
            await self._cleanup_session()
    
    async def _show_startup_with_tools(self):
        """Show startup animation using tool system."""
        context = ToolContext(
            tool_manager=self.tool_manager,
            mcp_service=self.mcp_service,
            config=self.config,
            current_path=str(self.cwd)
        )
        
        # Try to use animation tool for startup
        try:
            result = await self.tool_manager.process_request("startup animation", context)
            if result.success:
                self.logger.info("Startup animation completed")
        except Exception as e:
            self.logger.debug(f"Startup animation failed: {e}")
            # Simple fallback
            console.print("[bold cyan]🚀 Codexa Enhanced - Tool-Based Architecture[/bold cyan]")

    async def _main_loop(self):
        """Main interaction loop using tool-based request processing."""
        console.print("")  # Just a blank line, no repeated ready message
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]codexa>[/bold cyan]").strip()
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n[yellow]Goodbye! Happy coding! 🚀[/yellow]")
                    break
                
                if not user_input:
                    continue
                
                # Process request using tool manager
                await self._process_request_with_tools(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                self.logger.error(f"Main loop error: {e}")

    async def _process_request_with_tools(self, request: str):
        """Process user request using the tool-based architecture."""
        console.print(f"\n[blue4]Processing request with tools...[/blue4]")
        
        try:
            # Create tool context
            context = ToolContext(
                tool_manager=self.tool_manager,
                mcp_service=self.mcp_service,
                config=self.config,
                current_path=str(self.cwd),
                history=self.history
            )
            
            # Start performance tracking
            execution_id = None
            if self.tool_manager.performance_monitor:
                execution_id = self.tool_manager.performance_monitor.start_execution(
                    tool_name="request_processing",
                    request=request,
                    context_size=len(str(context))
                )
            
            # Use tool manager to process the request
            result = await self.tool_manager.process_request(request, context)
            
            # Complete performance tracking
            if execution_id and self.tool_manager.performance_monitor:
                self.tool_manager.performance_monitor.complete_execution(
                    execution_id, 
                    result,
                    confidence_score=0.8  # Default confidence for successful routing
                )
            
            if result.success:
                # Display result
                console.print("\n[bold green]Codexa:[/bold green]")
                if result.data:
                    # Format the result based on type
                    if isinstance(result.data, dict):
                        self._display_structured_result(result.data)
                    else:
                        console.print(Markdown(str(result.data)))
                
                # Save successful interactions to history
                self.history.append({
                    "user": request,
                    "assistant": self._format_result_message(result) or str(result.data),
                    "timestamp": datetime.now().isoformat(),
                    "tools_used": getattr(result, 'tools_used', [])
                })
                
            else:
                console.print(f"[red]Request failed: {self._format_result_message(result)}[/red]")
                if result.data and isinstance(result.data, dict) and 'error' in result.data:
                    console.print(f"[dim]Details: {result.data['error']}[/dim]")
        
        except Exception as e:
            console.print(f"[red]Request processing failed: {e}[/red]")
            self.logger.error(f"Request processing error: {e}")
    
    def _display_structured_result(self, data: dict):
        """Display structured result data in a user-friendly format."""
        if 'code' in data:
            # Code generation result
            console.print(f"[green]✅ {data.get('generation_type', 'Code')} generated![/green]")
            if 'language' in data:
                console.print(f"```{data['language']}\n{data['code']}\n```")
            else:
                console.print(f"```\n{data['code']}\n```")
        elif 'files' in data or 'results' in data:
            # Search or file operation results
            results = data.get('results', data.get('files', []))
            console.print(f"[green]Found {len(results)} result(s):[/green]")
            for result in results[:10]:  # Limit display
                if isinstance(result, dict):
                    if 'file' in result:
                        console.print(f"• {result['file']}")
                    elif 'name' in result:
                        console.print(f"• {result['name']}")
                else:
                    console.print(f"• {result}")
        elif 'message' in data:
            # Simple message result
            console.print(data['message'])
        else:
            # Generic structured data
            console.print(Markdown(f"```json\n{data}\n```"))

    def _format_result_message(self, result: object) -> str:
        """Return a human-friendly string for a ToolResult-like object.

        Prefer `output`, then `error`, then `data` (stringified).
        """
        # Prefer explicit output
        if hasattr(result, 'output') and result.output:
            return str(result.output)

        # Then error
        if hasattr(result, 'error') and result.error:
            return str(result.error)

        # Then data (strings preferred)
        if hasattr(result, 'data'):
            d = result.data
            if isinstance(d, str):
                return d
            try:
                return str(d)
            except Exception:
                return ''

        # Fallback
        try:
            return str(result)
        except Exception:
            return ''

    def initialize_project(self) -> None:
        """Initialize Codexa project using tool system where possible."""
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
        """Create enhanced CODEXA.md for tool-based architecture."""
        from datetime import datetime
        
        codexa_md_content = f"""# Codexa Guidelines - Tool-Based Architecture

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Project: {self.cwd.name}

## Tool-Based Architecture

### 🛠️ Available Tool Categories
- **Filesystem Tools**: File operations (read, write, create, delete, list, search)
- **MCP Tools**: Integration with Model Context Protocol servers
- **Enhanced Tools**: UI features (animations, themes, help, planning, code generation)

### 🚀 How It Works
Codexa now uses a dynamic tool system where:
- Each capability is implemented as an individual tool
- Tools are discovered automatically at startup  
- Requests are intelligently routed to appropriate tools
- Tools can work together to complete complex tasks

### 🎯 Natural Language Interface
You can make requests naturally:
- "Create a Python function for user authentication"
- "Search for files containing 'config'"  
- "Show me the help documentation"
- "Generate a React component for login"

## Role Definition
Codexa acts as an intelligent coding assistant that:

### Core Philosophy
- Routes requests to specialized tools automatically
- Provides fallback mechanisms when tools are unavailable
- Maintains project context across tool interactions
- Learns from tool usage patterns

### Development Approach  
- Intelligent tool selection based on request analysis
- Parallel tool execution for complex workflows
- Tool coordination for multi-step operations
- Context sharing across tool boundaries

### Communication Style
- Natural language processing for tool requests
- Clear feedback on which tools are being used
- Transparent error handling with tool-specific guidance
- Progressive assistance with increasing tool sophistication

## Project Context
This project is located at: `{self.cwd}`

Tool-based Codexa adapts its capabilities based on available tools and project structure.

---
*This file was automatically generated by Tool-Based Codexa. The agent uses dynamic tool discovery and intelligent routing.*"""

        codexa_md_path = self.cwd / "CODEXA.md"
        with open(codexa_md_path, "w", encoding="utf-8") as f:
            f.write(codexa_md_content)
        
        console.print(f"[green]✅ Created tool-based CODEXA.md[/green]")

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

    async def _cleanup_session(self):
        """Clean up session resources."""
        self.logger.info("Starting session cleanup...")
        
        try:
            # Stop MCP service
            if self.mcp_service:
                await self.mcp_service.stop()
            
            # Save configuration
            try:
                self.config.save_config()
            except Exception as e:
                self.logger.error(f"Failed to save config: {e}")
        
        except Exception as e:
            self.logger.error(f"Error during session cleanup: {e}")
        
        self.logger.info("Session cleanup complete")

    async def shutdown(self):
        """Graceful shutdown of tool-based agent."""
        self.logger.info("Shutting down tool-based Codexa agent...")
        await self._cleanup_session()
        self.logger.info("Shutdown complete")

    # Tool information methods for debugging/introspection
    def get_available_tools(self) -> Dict[str, Any]:
        """Get information about available tools."""
        return self.tool_registry.get_all_tools()
    
    def get_tool_status(self) -> Dict[str, Any]:
        """Get status of tool system."""
        return {
            "total_tools": len(self.tool_registry.get_all_tools()),
            "tool_manager_active": self.tool_manager is not None,
            "mcp_service_active": self.mcp_service is not None and hasattr(self.mcp_service, 'is_running') and self.mcp_service.is_running,
            "project_path": str(self.cwd)
        }
