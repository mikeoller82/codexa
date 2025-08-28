"""
Shared Event Loop Agent Implementation
Based on the architecture diagram with Agent -> Anthropic Client, Tool Registry, getUserMessage, and Verbose Logging.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from anthropic import Anthropic, AsyncAnthropic
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from .tools.base.tool_registry import ToolRegistry
from .tools.base.tool_interface import ToolContext
from .enhanced_config import EnhancedConfig


@dataclass
class ConversationMessage:
    """Represents a message in the conversation."""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass 
class ChatSession:
    """Represents a chat session with conversation history."""
    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


class SharedEventLoopAgent:
    """
    Shared Event Loop Agent following the architecture diagram.
    
    Components:
    - Agent -> Anthropic Client
    - Agent -> Tool Registry  
    - Agent -> getUserMessage Function
    - Agent -> Verbose Logging
    
    Event Loop:
    - Start Chat Session
    - Get User Input -> Handle Empty Input
    - Add to Conversation -> runInference -> Claude Response
    - Tool Use Decision -> Execute Tools/Display Text
    - Tool Execution Loop with error handling
    """
    
    def __init__(self, config: Optional[EnhancedConfig] = None):
        """Initialize the shared event loop agent."""
        # Core components from diagram
        self.config = config or EnhancedConfig()
        self._setup_verbose_logging()
        self._setup_anthropic_client()
        self._setup_tool_registry()
        self._setup_get_user_message_function()
        
        # Session management
        self.current_session: Optional[ChatSession] = None
        self.sessions: Dict[str, ChatSession] = {}
        
        # Event loop state
        self._running = False
        self._console = Console()
        
        self.logger.info("SharedEventLoopAgent initialized with all components")
    
    def _setup_verbose_logging(self):
        """Setup verbose logging component."""
        # Check if verbose logging is enabled in user config
        verbose_logging = self.config.user_config.get("features", {}).get("verbose_logging", True)
        
        logging.basicConfig(
            level=logging.DEBUG if verbose_logging else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('.codexa/agent.log') if hasattr(self, 'codexa_dir') else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger("SharedEventLoopAgent")
        self.logger.info("Verbose logging initialized")
    
    def _setup_anthropic_client(self):
        """Setup Anthropic client component."""
        api_key = self.config.get_api_key("anthropic") or self.config.get_api_key("openai")
        if not api_key:
            raise ValueError("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.")
        
        self.anthropic_client = AsyncAnthropic(api_key=api_key)
        self.logger.info("Anthropic client initialized")
    
    def _setup_tool_registry(self):
        """Setup tool registry component."""
        self.tool_registry = ToolRegistry()
        # Auto-discover tools
        discovered_count = self.tool_registry.discover_tools()
        self.logger.info(f"Tool registry initialized with {discovered_count} tools")
    
    def _setup_get_user_message_function(self):
        """Setup getUserMessage function component."""
        def get_user_message(prompt: str = "You") -> str:
            """Get user input with configurable prompt."""
            try:
                user_input = Prompt.ask(f"\n[bold cyan]{prompt}>[/bold cyan]").strip()
                self.logger.debug(f"User input received: {user_input[:100]}...")
                return user_input
            except KeyboardInterrupt:
                self.logger.info("User interrupted input")
                return "quit"
            except Exception as e:
                self.logger.error(f"Error getting user input: {e}")
                return ""
        
        self.get_user_message = get_user_message
        self.logger.info("getUserMessage function initialized")
    
    async def start_chat_session(self, session_id: Optional[str] = None) -> str:
        """Start a new chat session following the event loop diagram."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create new session
        session = ChatSession(session_id=session_id)
        self.sessions[session_id] = session
        self.current_session = session
        
        self.logger.info(f"Chat session started: {session_id}")
        self._console.print(f"[green]🚀 Chat session started: {session_id}[/green]")
        
        return session_id
    
    async def run_shared_event_loop(self):
        """Run the main shared event loop as shown in the diagram."""
        self._running = True
        
        # Start Chat Session
        if not self.current_session:
            await self.start_chat_session()
        
        self._console.print("[bold green]Shared Event Loop Agent Ready![/bold green]")
        self.logger.info("Entering main event loop")
        
        while self._running:
            try:
                # Get User Input
                user_input = self.get_user_message("codexa")
                
                # Empty Input? -> Continue to Get User Input
                if not user_input:
                    continue
                
                # Handle exit commands
                if user_input.lower() in ["exit", "quit", "bye"]:
                    self._console.print("[yellow]Goodbye! 👋[/yellow]")
                    break
                
                # Add to Conversation
                await self._add_to_conversation(user_input)
                
                # runInference -> Claude Response
                claude_response = await self._run_inference()
                
                # Tool Use Decision
                if await self._has_tool_use(claude_response):
                    # Execute Tools
                    await self._execute_tools(claude_response)
                else:
                    # Display Text
                    await self._display_text(claude_response)
                
                # Update session activity
                self.current_session.last_activity = datetime.now()
                
            except KeyboardInterrupt:
                self._console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                self.logger.error(f"Event loop error: {e}", exc_info=True)
                self._console.print(f"[red]Error in event loop: {e}[/red]")
        
        self._running = False
        self.logger.info("Event loop stopped")
    
    async def _add_to_conversation(self, user_input: str):
        """Add user message to conversation."""
        message = ConversationMessage(role="user", content=user_input)
        self.current_session.messages.append(message)
        self.logger.debug(f"Added user message to conversation: {user_input[:50]}...")
    
    async def _run_inference(self) -> Dict[str, Any]:
        """Run inference with Claude and return response."""
        try:
            # Prepare messages for API
            api_messages = []
            for msg in self.current_session.messages:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Get available tools
            available_tools = self._get_anthropic_tools()
            
            self.logger.debug(f"Running inference with {len(api_messages)} messages and {len(available_tools)} tools")
            
            # Call Claude API
            response = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=api_messages,
                tools=available_tools if available_tools else None
            )
            
            self.logger.debug("Claude response received")
            return response
            
        except Exception as e:
            self.logger.error(f"Inference failed: {e}")
            raise
    
    async def _has_tool_use(self, claude_response) -> bool:
        """Check if Claude response contains tool use."""
        if hasattr(claude_response, 'content'):
            for content_block in claude_response.content:
                if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    return True
        return False
    
    async def _execute_tools(self, claude_response):
        """Execute tools following the tool execution loop from diagram."""
        self.logger.info("Executing tools...")
        
        tool_results = []
        
        # Extract tool calls from response
        for content_block in claude_response.content:
            if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                # Tool Execution Loop
                result = await self._tool_execution_loop(content_block)
                tool_results.append(result)
        
        # Collect Results and Send Results to Claude
        await self._send_tool_results_to_claude(tool_results)
    
    async def _tool_execution_loop(self, tool_call) -> Dict[str, Any]:
        """Execute individual tool following the tool execution loop diagram."""
        tool_name = tool_call.name
        tool_input = tool_call.input
        tool_id = tool_call.id
        
        self.logger.debug(f"Tool execution loop: {tool_name}")
        
        try:
            # Find Tool by Name
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                return {
                    "tool_use_id": tool_id,
                    "type": "tool_result",
                    "content": f"Error: Tool not found: {tool_name}",
                    "is_error": True
                }
            
            # Execute Tool Function
            context = self._create_tool_context(tool_input)
            result = await tool.safe_execute(context)
            
            # Capture Result/Error
            if result.success:
                return {
                    "tool_use_id": tool_id,
                    "type": "tool_result", 
                    "content": result.output or str(result.data) or "Tool executed successfully",
                    "is_error": False
                }
            else:
                return {
                    "tool_use_id": tool_id,
                    "type": "tool_result",
                    "content": f"Error: {result.error}",
                    "is_error": True
                }
        
        except Exception as e:
            self.logger.error(f"Tool execution error: {tool_name} - {e}")
            return {
                "tool_use_id": tool_id,
                "type": "tool_result",
                "content": f"Tool execution error: {str(e)}",
                "is_error": True
            }
    
    async def _send_tool_results_to_claude(self, tool_results: List[Dict[str, Any]]):
        """Send tool results back to Claude and get final response."""
        # Add tool results to conversation
        tool_result_message = ConversationMessage(
            role="user",
            content=tool_results  # Claude expects tool results in this format
        )
        self.current_session.messages.append(tool_result_message)
        
        # Get Claude's final response
        final_response = await self._run_inference()
        await self._display_text(final_response)
    
    async def _display_text(self, claude_response):
        """Display text response from Claude."""
        if hasattr(claude_response, 'content'):
            for content_block in claude_response.content:
                if hasattr(content_block, 'type') and content_block.type == 'text':
                    text_content = content_block.text
                    self._console.print(text_content)
                    
                    # Add to conversation
                    assistant_message = ConversationMessage(role="assistant", content=text_content)
                    self.current_session.messages.append(assistant_message)
                    
                    self.logger.debug(f"Displayed text response: {text_content[:50]}...")
    
    def _create_tool_context(self, tool_input: Dict[str, Any]) -> ToolContext:
        """Create tool context for execution."""
        return ToolContext(
            request_id=str(uuid.uuid4()),
            user_request=str(tool_input),
            session_id=self.current_session.session_id,
            config=self.config,
            current_path=".",
            shared_state={"tool_input": tool_input}
        )
    
    def _get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get tools formatted for Anthropic API."""
        anthropic_tools = []
        
        for tool_name, tool_info in self.tool_registry.get_all_tools().items():
            if tool_info.instance:
                # Convert tool to Anthropic tool format
                tool_schema = {
                    "name": tool_name,
                    "description": tool_info.description,
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "string",
                                "description": "The request or parameters for the tool"
                            }
                        },
                        "required": ["request"]
                    }
                }
                anthropic_tools.append(tool_schema)
        
        self.logger.debug(f"Generated {len(anthropic_tools)} Anthropic tool schemas")
        return anthropic_tools
    
    def stop(self):
        """Stop the event loop."""
        self._running = False
        self.logger.info("Event loop stop requested")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about current session."""
        if not self.current_session:
            return {"error": "No active session"}
        
        return {
            "session_id": self.current_session.session_id,
            "message_count": len(self.current_session.messages),
            "started_at": self.current_session.started_at.isoformat(),
            "last_activity": self.current_session.last_activity.isoformat(),
            "context": self.current_session.context
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        return {
            "running": self._running,
            "current_session": self.current_session.session_id if self.current_session else None,
            "total_sessions": len(self.sessions),
            "tool_count": len(self.tool_registry.get_all_tools()),
            "anthropic_client_ready": self.anthropic_client is not None,
            "components": {
                "anthropic_client": bool(self.anthropic_client),
                "tool_registry": bool(self.tool_registry),
                "get_user_message": bool(self.get_user_message),
                "verbose_logging": bool(self.logger)
            }
        }


async def main():
    """Main entry point for testing the shared event loop agent."""
    try:
        config = EnhancedConfig()
        agent = SharedEventLoopAgent(config)
        
        print("Starting Shared Event Loop Agent...")
        await agent.run_shared_event_loop()
        
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Main error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())