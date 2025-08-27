"""
Intelligent contextual help and command discovery system for Codexa.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.syntax import Syntax

from ..commands.command_registry import CommandRegistry, Command, CommandCategory


class HelpType(Enum):
    """Types of help suggestions."""
    COMMAND_SUGGESTION = "command_suggestion"
    PARAMETER_HELP = "parameter_help"
    USAGE_EXAMPLE = "usage_example"
    TUTORIAL = "tutorial"
    ERROR_RECOVERY = "error_recovery"
    CONTEXT_AWARE = "context_aware"


@dataclass
class HelpSuggestion:
    """A contextual help suggestion."""
    type: HelpType
    title: str
    content: str
    relevance_score: float
    commands: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Sort by relevance score (descending)."""
        return self.relevance_score > other.relevance_score


@dataclass
class UserContext:
    """Context about user's current state and needs."""
    current_command: Optional[str] = None
    recent_commands: List[str] = field(default_factory=list)
    recent_errors: List[str] = field(default_factory=list)
    project_type: Optional[str] = None
    skill_level: str = "intermediate"  # beginner, intermediate, advanced
    preferences: Dict[str, Any] = field(default_factory=dict)
    session_time: timedelta = timedelta()


class ContextualHelpSystem:
    """Intelligent help system with contextual suggestions."""
    
    def __init__(self, command_registry: CommandRegistry, console: Optional[Console] = None):
        self.command_registry = command_registry
        self.console = console or Console()
        self.logger = logging.getLogger("contextual_help")
        
        # Help content knowledge base
        self.help_kb: Dict[str, Dict[str, Any]] = {}
        self.command_patterns: Dict[str, List[str]] = {}
        self.usage_examples: Dict[str, List[str]] = {}
        self.tutorials: Dict[str, str] = {}
        
        # User tracking
        self.user_contexts: Dict[str, UserContext] = {}
        self.command_usage_stats: Dict[str, int] = {}
        self.help_request_history: List[Tuple[str, datetime]] = []
        
        # Initialize knowledge base
        self._initialize_help_content()
    
    def _initialize_help_content(self):
        """Initialize help content knowledge base."""
        
        # Command patterns for suggestion
        self.command_patterns = {
            "status": ["check", "show", "display", "info", "current"],
            "provider": ["switch", "change", "ai", "model", "openai", "anthropic"],
            "mcp": ["server", "enable", "disable", "connect"],
            "help": ["?", "assistance", "guide", "how"],
            "config": ["configure", "setup", "settings", "preferences"]
        }
        
        # Usage examples
        self.usage_examples = {
            "status": [
                "/status - Show system status",
                "/status --detailed - Show detailed information"
            ],
            "provider": [
                "/provider list - Show available providers",
                "/provider switch openai - Switch to OpenAI",
                "/provider status - Show current provider info"
            ],
            "mcp": [
                "/mcp status - Check MCP service status",
                "/mcp enable context7 - Enable Context7 server",
                "/mcp query sequential 'analyze this code'"
            ],
            "model": [
                "/model list - Show available models", 
                "/model switch gpt-4o - Switch to GPT-4o",
                "/model info claude-3-5-sonnet - Get model information"
            ]
        }
        
        # Tutorials
        self.tutorials = {
            "getting_started": """
# Getting Started with Codexa

Welcome to Codexa! Here's a quick guide to get you up and running:

## 1. Check System Status
Use `/status` to see your current configuration and any issues.

## 2. Configure Your AI Provider
- `/provider list` - See available providers
- `/provider switch <name>` - Switch providers
- `/model list` - See available models

## 3. Enable MCP Servers (Optional)
- `/mcp list` - See available servers
- `/mcp enable context7` - Enable documentation server
- `/mcp enable sequential` - Enable reasoning server

## 4. Start Coding
Just describe what you want to build naturally, or use specific commands.

## 5. Get Help Anytime
- `/help` - General help
- `/help <command>` - Specific command help
- `/commands` - List all commands

Happy coding! 🚀
            """,
            
            "provider_management": """
# Managing AI Providers

Codexa supports multiple AI providers for maximum flexibility:

## Available Providers
- **OpenAI**: GPT models (requires OPENAI_API_KEY)
- **Anthropic**: Claude models (requires ANTHROPIC_API_KEY)
- **OpenRouter**: Various models (requires OPENROUTER_API_KEY)

## Commands
- `/provider list` - Show available providers
- `/provider switch <name>` - Change provider
- `/provider status` - Show current status
- `/model list` - Show models for current provider
- `/model switch <name>` - Change model

## Tips
- Codexa automatically falls back to available providers
- Different models excel at different tasks
- Use `/status` to check provider health
            """,
            
            "mcp_servers": """
# MCP Server Integration

MCP servers enhance Codexa with specialized capabilities:

## Available Servers
- **Context7**: Documentation and code examples
- **Sequential**: Complex reasoning and analysis
- **Magic**: UI component generation
- **Playwright**: Cross-browser testing

## Commands
- `/mcp status` - Check MCP service
- `/mcp list` - Show available servers
- `/mcp enable <server>` - Enable server
- `/mcp disable <server>` - Disable server
- `/mcp query <server> "request"` - Direct query

## Benefits
- Enhanced documentation lookup
- Better code analysis
- UI component generation
- Cross-browser testing
            """
        }
    
    def get_contextual_help(self, query: str, user_id: str = "default", 
                          context: Optional[Dict[str, Any]] = None) -> List[HelpSuggestion]:
        """Get contextual help suggestions for a query."""
        # Get or create user context
        user_ctx = self.user_contexts.get(user_id, UserContext())
        
        # Update context with current query
        if context:
            if "current_command" in context:
                user_ctx.current_command = context["current_command"]
            if "recent_errors" in context:
                user_ctx.recent_errors.extend(context["recent_errors"])
        
        suggestions = []
        
        # Analyze query for intent
        intent = self._analyze_query_intent(query)
        
        # Generate different types of suggestions
        suggestions.extend(self._generate_command_suggestions(query, user_ctx, intent))
        suggestions.extend(self._generate_parameter_help(query, user_ctx))
        suggestions.extend(self._generate_usage_examples(query, user_ctx))
        suggestions.extend(self._generate_tutorials(query, user_ctx))
        suggestions.extend(self._generate_error_recovery(query, user_ctx))
        suggestions.extend(self._generate_context_aware_help(query, user_ctx, context))
        
        # Sort by relevance and return top suggestions
        suggestions.sort()
        return suggestions[:10]
    
    def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze user query to understand intent."""
        query_lower = query.lower()
        
        intent = {
            "type": "general",
            "commands": [],
            "topics": [],
            "urgency": "normal",
            "complexity": "simple"
        }
        
        # Check for command references
        command_pattern = r'/(\w+)'
        commands = re.findall(command_pattern, query)
        intent["commands"] = commands
        
        # Check for specific topics
        topic_keywords = {
            "provider": ["provider", "openai", "anthropic", "model", "ai"],
            "mcp": ["mcp", "server", "context7", "sequential", "magic"],
            "status": ["status", "check", "show", "info"],
            "config": ["config", "setup", "configure", "settings"],
            "error": ["error", "failed", "not working", "broken", "issue"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                intent["topics"].append(topic)
        
        # Determine urgency
        urgent_keywords = ["urgent", "critical", "broken", "not working", "error", "failed"]
        if any(keyword in query_lower for keyword in urgent_keywords):
            intent["urgency"] = "high"
        
        # Determine complexity
        complex_keywords = ["advanced", "detailed", "comprehensive", "in-depth"]
        simple_keywords = ["simple", "quick", "basic", "easy"]
        
        if any(keyword in query_lower for keyword in complex_keywords):
            intent["complexity"] = "complex"
        elif any(keyword in query_lower for keyword in simple_keywords):
            intent["complexity"] = "simple"
        
        return intent
    
    def _generate_command_suggestions(self, query: str, user_ctx: UserContext, 
                                    intent: Dict[str, Any]) -> List[HelpSuggestion]:
        """Generate command suggestions."""
        suggestions = []
        query_lower = query.lower()
        
        # Find commands that match query patterns
        for command_name, patterns in self.command_patterns.items():
            relevance = 0.0
            
            # Direct command name match
            if command_name in query_lower:
                relevance += 0.8
            
            # Pattern matching
            pattern_matches = sum(1 for pattern in patterns if pattern in query_lower)
            relevance += pattern_matches * 0.3
            
            # Intent-based boost
            if command_name in intent.get("topics", []):
                relevance += 0.5
            
            if relevance > 0.3:
                # Get command help
                command = self.command_registry.get_command(command_name)
                if command:
                    suggestion = HelpSuggestion(
                        type=HelpType.COMMAND_SUGGESTION,
                        title=f"Command: /{command_name}",
                        content=command.description,
                        relevance_score=relevance,
                        commands=[command_name],
                        examples=self.usage_examples.get(command_name, []),
                        metadata={"category": command.category.value}
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_parameter_help(self, query: str, user_ctx: UserContext) -> List[HelpSuggestion]:
        """Generate parameter-specific help."""
        suggestions = []
        
        # Check if query mentions a specific command
        command_match = re.search(r'/(\w+)', query)
        if command_match:
            command_name = command_match.group(1)
            command = self.command_registry.get_command(command_name)
            
            if command and command.parameters:
                param_help = []
                for param in command.parameters:
                    param_desc = f"**{param.name}** ({param.type.__name__})"
                    if param.required:
                        param_desc += " [required]"
                    else:
                        param_desc += " [optional]"
                    
                    if param.default is not None:
                        param_desc += f" [default: {param.default}]"
                    
                    param_desc += f" - {param.description}"
                    param_help.append(param_desc)
                
                suggestion = HelpSuggestion(
                    type=HelpType.PARAMETER_HELP,
                    title=f"Parameters for /{command_name}",
                    content="\n".join(param_help),
                    relevance_score=0.9,
                    commands=[command_name]
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_usage_examples(self, query: str, user_ctx: UserContext) -> List[HelpSuggestion]:
        """Generate usage examples."""
        suggestions = []
        query_lower = query.lower()
        
        # Look for example requests
        if any(word in query_lower for word in ["example", "how to", "usage", "demo"]):
            for command_name, examples in self.usage_examples.items():
                if command_name in query_lower or any(pattern in query_lower 
                                                    for pattern in self.command_patterns.get(command_name, [])):
                    
                    suggestion = HelpSuggestion(
                        type=HelpType.USAGE_EXAMPLE,
                        title=f"Usage Examples: /{command_name}",
                        content="\n".join(examples),
                        relevance_score=0.7,
                        commands=[command_name],
                        examples=examples
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_tutorials(self, query: str, user_ctx: UserContext) -> List[HelpSuggestion]:
        """Generate tutorial suggestions."""
        suggestions = []
        query_lower = query.lower()
        
        # Check for tutorial requests
        tutorial_keywords = ["tutorial", "guide", "getting started", "learn", "how to"]
        if any(keyword in query_lower for keyword in tutorial_keywords):
            
            for tutorial_name, content in self.tutorials.items():
                relevance = 0.5
                
                # Topic matching
                if "getting started" in query_lower and tutorial_name == "getting_started":
                    relevance = 0.9
                elif "provider" in query_lower and tutorial_name == "provider_management":
                    relevance = 0.8
                elif "mcp" in query_lower and tutorial_name == "mcp_servers":
                    relevance = 0.8
                
                if relevance > 0.4:
                    suggestion = HelpSuggestion(
                        type=HelpType.TUTORIAL,
                        title=tutorial_name.replace("_", " ").title(),
                        content=content.strip(),
                        relevance_score=relevance,
                        metadata={"tutorial": tutorial_name}
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_error_recovery(self, query: str, user_ctx: UserContext) -> List[HelpSuggestion]:
        """Generate error recovery suggestions."""
        suggestions = []
        
        # Check recent errors in user context
        if user_ctx.recent_errors:
            latest_error = user_ctx.recent_errors[-1]
            
            # Common error patterns and solutions
            error_solutions = {
                "permission denied": "Check your API keys and permissions. Use `/config show` to verify setup.",
                "not found": "The command or resource wasn't found. Use `/commands` to see available commands.",
                "timeout": "Request timed out. Check your network connection and try again.",
                "invalid": "Invalid input provided. Use `/help <command>` for correct usage.",
                "server unavailable": "MCP server is not available. Use `/mcp status` to check servers."
            }
            
            for pattern, solution in error_solutions.items():
                if pattern in latest_error.lower():
                    suggestion = HelpSuggestion(
                        type=HelpType.ERROR_RECOVERY,
                        title=f"Error Recovery: {pattern.title()}",
                        content=solution,
                        relevance_score=0.8,
                        metadata={"error_pattern": pattern}
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_context_aware_help(self, query: str, user_ctx: UserContext, 
                                   context: Optional[Dict[str, Any]]) -> List[HelpSuggestion]:
        """Generate context-aware help suggestions."""
        suggestions = []
        
        if not context:
            return suggestions
        
        # Project-specific suggestions
        if context.get("project_type"):
            project_type = context["project_type"]
            
            project_suggestions = {
                "react": "For React projects, try `/mcp enable magic` for UI component generation.",
                "python": "For Python projects, enable MCP servers for enhanced code analysis.",
                "nodejs": "For Node.js projects, consider enabling Context7 for documentation."
            }
            
            if project_type in project_suggestions:
                suggestion = HelpSuggestion(
                    type=HelpType.CONTEXT_AWARE,
                    title=f"Suggestion for {project_type.title()} Project",
                    content=project_suggestions[project_type],
                    relevance_score=0.6,
                    metadata={"project_type": project_type}
                )
                suggestions.append(suggestion)
        
        # Provider-specific suggestions
        if context.get("provider_issues"):
            suggestion = HelpSuggestion(
                type=HelpType.CONTEXT_AWARE,
                title="Provider Issues Detected",
                content="Consider switching providers with `/provider switch <name>` or check API keys.",
                relevance_score=0.7,
                commands=["provider"]
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def display_help(self, suggestions: List[HelpSuggestion], limit: int = 5):
        """Display help suggestions in a formatted way."""
        if not suggestions:
            self.console.print("[yellow]No help suggestions found.[/yellow]")
            return
        
        self.console.print(f"\n[bold cyan]💡 Help Suggestions ({len(suggestions[:limit])} of {len(suggestions)}):[/bold cyan]")
        
        for i, suggestion in enumerate(suggestions[:limit], 1):
            # Format suggestion based on type
            icon = self._get_suggestion_icon(suggestion.type)
            panel_style = self._get_suggestion_style(suggestion.type)
            
            content_text = suggestion.content
            
            # Add examples if available
            if suggestion.examples:
                content_text += f"\n\n[dim]Examples:[/dim]\n"
                content_text += "\n".join(f"  {example}" for example in suggestion.examples[:3])
            
            panel = Panel(
                content_text,
                title=f"{icon} {suggestion.title}",
                border_style=panel_style,
                padding=(0, 1)
            )
            
            self.console.print(panel)
        
        if len(suggestions) > limit:
            self.console.print(f"[dim]... and {len(suggestions) - limit} more suggestions available[/dim]")
    
    def _get_suggestion_icon(self, help_type: HelpType) -> str:
        """Get icon for help suggestion type."""
        icons = {
            HelpType.COMMAND_SUGGESTION: "⚡",
            HelpType.PARAMETER_HELP: "📝",
            HelpType.USAGE_EXAMPLE: "💻", 
            HelpType.TUTORIAL: "📚",
            HelpType.ERROR_RECOVERY: "🔧",
            HelpType.CONTEXT_AWARE: "🎯"
        }
        return icons.get(help_type, "ℹ️")
    
    def _get_suggestion_style(self, help_type: HelpType) -> str:
        """Get panel style for help suggestion type."""
        styles = {
            HelpType.COMMAND_SUGGESTION: "cyan",
            HelpType.PARAMETER_HELP: "yellow",
            HelpType.USAGE_EXAMPLE: "green",
            HelpType.TUTORIAL: "blue", 
            HelpType.ERROR_RECOVERY: "red",
            HelpType.CONTEXT_AWARE: "magenta"
        }
        return styles.get(help_type, "white")
    
    def update_user_context(self, user_id: str, **updates):
        """Update user context with new information."""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = UserContext()
        
        user_ctx = self.user_contexts[user_id]
        
        for key, value in updates.items():
            if hasattr(user_ctx, key):
                setattr(user_ctx, key, value)
    
    def record_command_usage(self, command: str, user_id: str = "default"):
        """Record command usage for better suggestions."""
        self.command_usage_stats[command] = self.command_usage_stats.get(command, 0) + 1
        
        # Update user's recent commands
        if user_id in self.user_contexts:
            user_ctx = self.user_contexts[user_id]
            user_ctx.recent_commands.append(command)
            # Keep only last 10 commands
            user_ctx.recent_commands = user_ctx.recent_commands[-10:]
    
    def record_help_request(self, query: str):
        """Record help request for analytics."""
        self.help_request_history.append((query, datetime.now()))
        
        # Keep only last 100 requests
        self.help_request_history = self.help_request_history[-100:]
    
    def get_help_analytics(self) -> Dict[str, Any]:
        """Get analytics on help usage."""
        return {
            "total_help_requests": len(self.help_request_history),
            "most_used_commands": sorted(self.command_usage_stats.items(), 
                                       key=lambda x: x[1], reverse=True)[:10],
            "active_users": len(self.user_contexts),
            "recent_requests": len([req for req in self.help_request_history 
                                  if (datetime.now() - req[1]).hours < 24])
        }
    
    async def show_main_help(self, **kwargs):
        """Show main help information with contextual assistance."""
        from rich.panel import Panel
        
        # Extract context information
        current_context = kwargs.get('current_context', {})
        available_commands = kwargs.get('available_commands', [])
        mcp_servers = kwargs.get('mcp_servers', [])
        
        # Show main help panel
        help_content = """Welcome to Codexa! 🚀

[bold cyan]Getting Started:[/bold cyan]
• Type your coding questions or requests in natural language
• Use slash commands like /help, /status, /config for specific functions
• Type 'exit' or 'quit' to leave

[bold cyan]Features Available:[/bold cyan]
• Natural language code assistance
• File generation and modification
• Project analysis and suggestions
• Interactive help system"""
        
        if available_commands:
            help_content += f"\n\n[bold cyan]Available Commands:[/bold cyan]\n"
            help_content += ", ".join(f"/{cmd}" for cmd in available_commands[:10])
            if len(available_commands) > 10:
                help_content += f" ... and {len(available_commands) - 10} more"
        
        if mcp_servers:
            help_content += f"\n\n[bold cyan]Active MCP Servers:[/bold cyan]\n"
            help_content += ", ".join(mcp_servers)
        
        help_panel = Panel(
            help_content,
            title="[bold green]Codexa Assistant Help[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(help_panel)
        
        # Show contextual suggestions if we have query context
        if current_context:
            suggestions = self.get_contextual_help("help", context=current_context)
            if suggestions:
                self.console.print("\n[bold cyan]💡 Based on your current context:[/bold cyan]")
                self.display_help(suggestions, limit=3)