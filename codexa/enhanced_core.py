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

# Command system
from .commands.command_registry import CommandRegistry
from .commands.built_in_commands import BuiltInCommands

# Configuration and providers
from .enhanced_config import EnhancedConfig
from .enhanced_providers import EnhancedProviderFactory
from .mcp_service import MCPService

# Session memory integration
try:
    from .session_memory import SessionMemory
    SESSION_MEMORY_AVAILABLE = True
except ImportError:
    SessionMemory = None
    SESSION_MEMORY_AVAILABLE = False

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
        self.tool_manager = ToolManager(registry=self.tool_registry, auto_discover=False, enable_performance_monitoring=True)
        
        # Command system
        self.command_registry = CommandRegistry()
        BuiltInCommands.register_all(self.command_registry)
        
        # Session memory integration
        self.session_memory = None
        if SESSION_MEMORY_AVAILABLE:
            try:
                self.session_memory = SessionMemory(self.codexa_dir / "sessions")
                self.logger.info("Session memory initialized")
            except Exception as e:
                self.logger.warning(f"Session memory initialization failed: {e}")
        
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
            current_path=str(self.cwd),
            provider=self.provider
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
        
        # Load existing session if available
        if self.session_memory:
            try:
                # Try to load the most recent session
                latest_session = self._find_latest_session()
                if latest_session and self.session_memory.load_session(latest_session):
                    if self.session_memory.current_state.value in ["agentic_active", "agentic_paused"]:
                        console.print("\n[yellow]🔄 Resuming agentic task context...[/yellow]")
                        console.print(f"[dim]{self.session_memory.get_agentic_summary()}[/dim]\n")
                    else:
                        console.print(f"[dim]Session {latest_session} loaded[/dim]")
            except Exception as e:
                self.logger.debug(f"Failed to load previous session: {e}")
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]codexa>[/bold cyan]").strip()
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n[yellow]Goodbye! Happy coding! 🚀[/yellow]")
                    break
                
                if not user_input:
                    continue
                
                # Process request using tool manager with session memory awareness
                await self._process_request_with_tools(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                self.logger.error(f"Main loop error: {e}")

    async def _process_request_with_tools(self, request: str):
        """Process user request using the tool-based architecture with agentic capabilities."""
        
        # Check if this request is related to an existing agentic task
        is_agentic_continuation = False
        if self.session_memory:
            is_agentic_continuation = self.session_memory.is_request_related_to_agentic_task(request)
            
            # Add conversation entry
            self.session_memory.add_conversation_entry(request, "", "processing")
        
        # Determine processing mode - prioritize agentic mode for better task completion
        should_use_agentic = (
            is_agentic_continuation or 
            self._should_use_agentic_mode(request) or
            (self.session_memory and self.session_memory.should_continue_agentic_mode(request))
        )
        
        if should_use_agentic:
            await self._process_request_agentic(request, is_continuation=is_agentic_continuation)
        else:
            await self._process_request_direct(request)
    
    def _should_use_agentic_mode(self, request: str) -> bool:
        """Determine if request should use agentic loop mode - more aggressive detection."""
        request_lower = request.lower()
        
        # Explicit agentic commands
        if any(cmd in request_lower for cmd in ['/agentic', '/loop', '/autonomous', '/think']):
            return True
        
        # High-priority agentic keywords that trigger agentic mode by themselves
        high_priority_keywords = [
            'systematically', 'comprehensive', 'analyze', 'figure out', 
            'investigate', 'step by step', 'think through', 'solve',
            'implement', 'create', 'build', 'make', 'write', 'develop'
        ]
        
        if any(keyword in request_lower for keyword in high_priority_keywords):
            return True
        
        # Programming/development tasks are typically complex enough for agentic mode
        programming_keywords = [
            'function', 'class', 'method', 'variable', 'code', 'script',
            'program', 'application', 'algorithm', 'calculator', 'parser',
            'api', 'endpoint', 'server', 'client', 'database', 'file'
        ]
        
        programming_count = sum(1 for keyword in programming_keywords if keyword in request_lower)
        if programming_count >= 1:
            return True
        
        # Additional agentic indicators
        agentic_keywords = [
            'autonomously', 'iteratively', 'work through', 'debug',
            'complex', 'thorough', 'understand', 'improve', 'optimize',
            'design', 'architecture', 'structure', 'organize', 'refactor'
        ]
        
        keyword_count = sum(1 for keyword in agentic_keywords if keyword in request_lower)
        
        # Use agentic mode for multiple indicators, longer requests, or any programming task
        return (
            keyword_count >= 1 or  # Even single agentic indicator now triggers
            len(request) > 80 or   # Shorter threshold for complex requests  
            any(word in request_lower for word in ['how do i', 'how can i', 'help me'])  # Help requests
        )
    
    async def _process_request_agentic(self, request: str, is_continuation: bool = False):
        """Process request using agentic loop with verbose feedback."""
        if is_continuation:
            console.print(f"\n[bold cyan]🔄 Continuing Agentic Task[/bold cyan]")
            console.print(f"[dim]Continuing with related request: {request[:80]}{'...' if len(request) > 80 else ''}[/dim]\n")
        else:
            console.print(f"\n[bold cyan]🤖 Activating Agentic Mode[/bold cyan]")
            console.print(f"[dim]Request appears to require autonomous thinking and iteration...[/dim]\n")
        
        try:
            # Import agentic loop
            from .agentic_loop import create_agentic_loop
            
            # Create agentic loop with verbose mode enabled and session memory integration
            loop = create_agentic_loop(
                config=self.config,
                max_iterations=20,
                verbose=True,  # Always verbose for the enhanced experience
                session_memory=self.session_memory
            )
            
            # Enhance the loop with tool manager integration
            loop.tool_manager = self.tool_manager
            loop.mcp_service = self.mcp_service
            
            # Run the agentic loop
            result = await loop.run_agentic_loop(request)
            
            # Export session context for continuity
            exported_context = loop.export_session_context()
            
            # Determine if the agentic task should continue based on context
            should_pause_not_end = False
            if exported_context and not exported_context.get("is_task_complete", True):
                should_pause_not_end = True
                
                # Show continuation status
                if exported_context.get("should_continue", False):
                    pending_count = len(exported_context.get("pending_steps", []))
                    console.print(f"\n[yellow]📋 Agentic task paused with {pending_count} pending steps.[/yellow]")
                    console.print("[dim]Continue the conversation for automatic resumption.[/dim]")
                    
                    # Pause instead of ending the agentic context
                    if self.session_memory:
                        self.session_memory.pause_agentic_context()
            
            # Store results in history with enhanced context
            assistant_response = result.final_result or "Task processed via agentic loop"
            
            self.history.append({
                "user": request,
                "assistant": assistant_response,
                "timestamp": datetime.now().isoformat(),
                "mode": "agentic",
                "iterations": len(result.iterations),
                "success": result.success,
                "context_exported": exported_context is not None,
                "task_complete": exported_context.get("is_task_complete", True) if exported_context else True,
                "should_continue": exported_context.get("should_continue", False) if exported_context else False
            })
            
            # Update session memory with conversation entry
            if self.session_memory:
                self.session_memory.add_conversation_entry(request, assistant_response, "agentic")
            
        except ImportError:
            console.print("[red]❌ Agentic loop not available, falling back to direct processing...[/red]\n")
            await self._process_request_direct(request)
        except Exception as e:
            console.print(f"[red]❌ Agentic processing failed: {e}[/red]")
            console.print(f"[yellow]Falling back to direct processing...[/yellow]\n")
            await self._process_request_direct(request)
    
    async def _process_request_direct(self, request: str):
        """Process request using direct tool coordination with verbose feedback."""
        console.print(f"\n[blue4]🔧 Processing with tool coordination...[/blue4]")

        try:
            # Create tool context
            context = ToolContext(
                tool_manager=self.tool_manager,
                mcp_service=self.mcp_service,
                config=self.config,
                current_path=str(self.cwd),
                history=self.history,
                user_request=request,
                provider=self.provider
            )

            # Extract and set file paths from request for tools that need them
            self._extract_and_set_file_paths(request, context)

            # Show real-time tool discovery and planning
            console.print("[dim]🔍 Analyzing request and selecting tools...[/dim]")

            # Start performance tracking
            execution_id = None
            if self.tool_manager.performance_monitor:
                execution_id = self.tool_manager.performance_monitor.start_execution(
                    tool_name="request_processing",
                    request=request,
                    context_size=len(str(context))
                )

            # Use tool manager to process the request with verbose feedback
            result = await self.tool_manager.process_request(
                request,
                context,
                enable_coordination=True,
                max_tools=5,
                verbose=True  # Enable verbose feedback for real-time progress
            )

            # Complete performance tracking
            if execution_id and self.tool_manager.performance_monitor:
                self.tool_manager.performance_monitor.complete_execution(
                    execution_id,
                    result,
                    confidence_score=0.8  # Default confidence for successful routing
                )

            if result.success:
                # Display result - no need for "Codexa:" prefix in most cases
                if result.data:
                    # Format the result based on type
                    if isinstance(result.data, dict):
                        self._display_structured_result(result.data)
                    else:
                        clean_message = str(result.data).strip()
                        if clean_message and not clean_message.startswith('Task completed'):
                            console.print(clean_message)
                        else:
                            console.print("[dim]Task completed.[/dim]")
                else:
                    # Show clean output or error from result
                    message = self._format_result_message(result)
                    if message and message.strip():
                        console.print(message)

                # Save successful interactions to history
                assistant_response = self._format_result_message(result) or str(result.data)
                self.history.append({
                    "user": request,
                    "assistant": assistant_response,
                    "timestamp": datetime.now().isoformat(),
                    "tools_used": getattr(result, 'tools_used', [])
                })

                # Update session memory with conversation entry
                if self.session_memory:
                    self.session_memory.add_conversation_entry(request, assistant_response, "direct")

            else:
                # Enhanced error handling with fallback to direct AI processing
                error_message = self._format_result_message(result)
                console.print(f"[yellow]⚠️ Tool processing failed, trying direct AI response...[/yellow]")

                # Fallback to direct AI processing for natural language requests
                try:
                    fallback_response = await self._process_with_ai_fallback(request)
                    if fallback_response:
                        console.print(fallback_response)
                        # Save fallback response to history
                        self.history.append({
                            "user": request,
                            "assistant": fallback_response,
                            "timestamp": datetime.now().isoformat(),
                            "fallback": True
                        })
                        if self.session_memory:
                            self.session_memory.add_conversation_entry(request, fallback_response, "fallback")
                        return  # Success via fallback
                except Exception as fallback_error:
                    self.logger.error(f"Fallback processing failed: {fallback_error}")

                # If fallback also fails, show the original error
                console.print(f"[red]Request failed: {error_message}[/red]")
                if result.data and isinstance(result.data, dict) and 'error' in result.data:
                    console.print(f"[dim]Details: {result.data['error']}[/dim]")

        except Exception as e:
            console.print(f"[red]Request processing failed: {e}[/red]")
            self.logger.error(f"Request processing error: {e}")

    def _extract_and_set_file_paths(self, request: str, context: ToolContext):
        """Extract file paths from user request and set them in context for tools that need them."""
        import re

        # Look for file paths with extensions
        file_pattern = r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        matches = re.findall(file_pattern, request)

        if matches:
            # Set the first file path found
            context.update_state("file_path", matches[0])
            self.logger.debug(f"Extracted file_path from request: {matches[0]}")

        # Also look for quoted paths
        quoted_pattern = r'["\']([^"\']+)["\']'
        matches = re.findall(quoted_pattern, request)

        for match in matches:
            if '/' in match or '\\' in match or '.' in match:
                context.update_state("file_path", match)
                self.logger.debug(f"Extracted quoted file_path from request: {match}")
                break

    async def _process_with_ai_fallback(self, request: str) -> Optional[str]:
        """Fallback to direct AI processing when tool system fails."""
        try:
            # Get project context
            context_parts = []

            # Add CODEXA.md content
            codexa_md = self.cwd / "CODEXA.md"
            if codexa_md.exists():
                with open(codexa_md, "r", encoding="utf-8") as f:
                    context_parts.append(f"Project Guidelines:\n{f.read()}")

            # Add basic project info
            context_parts.append(f"Current Directory: {self.cwd}")

            # Add file listing (basic)
            files = []
            for item in self.cwd.iterdir():
                if not item.name.startswith('.') and item.is_file():
                    files.append(item.name)

            if files:
                context_parts.append(f"Files in project: {', '.join(files[:10])}")

            project_context = "\n\n".join(context_parts)

            # Use AI provider directly
            response = await self.provider.ask_async(
                prompt=request,
                history=self.history,
                context=project_context
            )

            if response:
                return response

        except Exception as e:
            self.logger.error(f"AI fallback failed: {e}")

        return None
    
    def _display_structured_result(self, data: dict):
        """Display structured result data in a user-friendly format."""
        # Handle coordination results first - these are the most common now
        if 'coordination_result' in data:
            self._display_coordination_result(data['coordination_result'])
            return
        elif 'tool_results' in data and 'successful_tools' in data:
            # Direct coordination data
            self._display_tool_results(data['tool_results'])
            return
        elif 'code' in data:
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
            # Generic structured data - avoid dumping raw objects
            clean_message = self._extract_clean_message(data)
            if clean_message:
                console.print(clean_message)
            else:
                console.print("[dim]Task completed successfully.[/dim]")

    def _display_coordination_result(self, coordination_result):
        """Display coordination result in a clean, user-friendly way."""
        if hasattr(coordination_result, 'tool_results'):
            self._display_tool_results(coordination_result.tool_results)
        else:
            # Fallback for unexpected coordination result format
            console.print("[dim]Task completed.[/dim]")
    
    def _display_tool_results(self, tool_results: dict):
        """Extract and display clean responses from tool results."""
        for tool_name, tool_result in tool_results.items():
            clean_response = self._extract_tool_response(tool_result)
            if clean_response:
                console.print(clean_response)
                return  # Only show the first meaningful response
        
        # If no clean response found, show generic success
        console.print("[dim]Task completed successfully.[/dim]")
    
    def _extract_tool_response(self, tool_result) -> str:
        """Extract clean, user-facing response from a tool result."""
        if not tool_result or not hasattr(tool_result, 'success') or not tool_result.success:
            return None
        
        # Check for conversational response in data
        if hasattr(tool_result, 'data') and isinstance(tool_result.data, dict):
            data = tool_result.data
            if 'response' in data:
                return str(data['response'])
            elif 'message' in data:
                return str(data['message'])
            elif 'output' in data:
                return str(data['output'])
        
        # Check for direct output
        if hasattr(tool_result, 'output') and tool_result.output:
            return str(tool_result.output)
        
        return None
    
    def _extract_clean_message(self, data) -> str:
        """Extract a clean message from complex data structures."""
        # Handle nested data structures
        if isinstance(data, dict):
            # Look for common response fields
            for key in ['response', 'message', 'output', 'content']:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        
        return None

    def _format_result_message(self, result: object) -> str:
        """Return a human-friendly string for a ToolResult-like object.

        Now handles coordination results properly.
        """
        # Handle coordination results first
        if hasattr(result, 'data') and isinstance(result.data, dict):
            data = result.data
            
            # Handle coordination result data
            if 'coordination_result' in data:
                return self._extract_coordination_message(data['coordination_result'])
            elif 'tool_results' in data:
                return self._extract_tool_results_message(data['tool_results'])
        
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
            # Try to extract clean message instead of dumping raw data
            clean_msg = self._extract_clean_message(d)
            if clean_msg:
                return clean_msg

        # Fallback - avoid raw object dumps
        return "Task completed."
    
    def _extract_coordination_message(self, coordination_result) -> str:
        """Extract clean message from coordination result."""
        if hasattr(coordination_result, 'tool_results'):
            return self._extract_tool_results_message(coordination_result.tool_results)
        return "Task completed."
    
    def _extract_tool_results_message(self, tool_results) -> str:
        """Extract clean message from tool results."""
        for tool_name, tool_result in tool_results.items():
            clean_response = self._extract_tool_response(tool_result)
            if clean_response:
                return clean_response
        return "Task completed."

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
            
            # Save and cleanup session memory
            if self.session_memory:
                try:
                    # If there's an active agentic context, end it gracefully
                    if self.session_memory.agentic_context:
                        self.session_memory.end_agentic_context()
                    
                    # Final save of session state
                    self.session_memory.save_session()
                    
                    # Cleanup old sessions
                    self.session_memory.cleanup_old_sessions(max_age_days=7)
                    
                    self.logger.info("Session memory cleanup complete")
                except Exception as e:
                    self.logger.error(f"Session memory cleanup failed: {e}")
            
            # Save configuration
            try:
                self.config.save_config()
            except Exception as e:
                self.logger.error(f"Failed to save config: {e}")
        
        except Exception as e:
            self.logger.error(f"Error during session cleanup: {e}")
        
        self.logger.info("Session cleanup complete")

    def _find_latest_session(self) -> Optional[str]:
        """Find the most recent session ID."""
        try:
            if not self.session_memory.session_dir.exists():
                return None
            
            session_files = list(self.session_memory.session_dir.glob("session_*.json"))
            if not session_files:
                return None
            
            # Sort by modification time, most recent first
            latest_file = max(session_files, key=lambda f: f.stat().st_mtime)
            
            # Extract session ID from filename
            session_id = latest_file.stem.replace("session_", "")
            return session_id
            
        except Exception as e:
            self.logger.debug(f"Failed to find latest session: {e}")
            return None
    
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
