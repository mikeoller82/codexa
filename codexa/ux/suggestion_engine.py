"""
Intelligent suggestion engine for enhanced Codexa UX.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text


class SuggestionType(Enum):
    """Types of suggestions."""
    COMMAND = "command"
    WORKFLOW = "workflow"
    OPTIMIZATION = "optimization"
    LEARNING = "learning"
    TROUBLESHOOTING = "troubleshooting"
    FEATURE = "feature"
    PROJECT_SETUP = "project_setup"


@dataclass
class Suggestion:
    """A contextual suggestion for the user."""
    type: SuggestionType
    title: str
    description: str
    action: str  # What the user should do
    priority: int = 1  # 1-5, higher = more important
    context_match: float = 0.5  # 0-1, how well it matches current context
    commands: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    estimated_time: str = "2-5 minutes"
    
    @property
    def score(self) -> float:
        """Calculate suggestion relevance score."""
        return (self.priority * 0.4) + (self.context_match * 0.6)
    
    def __lt__(self, other):
        """Sort by score (descending)."""
        return self.score > other.score


class SuggestionEngine:
    """Intelligent suggestion engine for enhanced UX."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("suggestion_engine")
        
        # User behavior tracking
        self.user_actions: List[Tuple[str, datetime]] = []
        self.user_preferences: Dict[str, Any] = {}
        self.project_context: Dict[str, Any] = {}
        
        # Suggestion knowledge base
        self.suggestion_rules: List[callable] = []
        self.context_analyzers: List[callable] = []
        
        # Initialize with built-in rules
        self._initialize_suggestion_rules()
        self._initialize_context_analyzers()
    
    def _initialize_suggestion_rules(self):
        """Initialize built-in suggestion rules."""
        
        def new_user_suggestions(context: Dict[str, Any]) -> List[Suggestion]:
            """Suggestions for new users."""
            suggestions = []
            
            if context.get("session_count", 0) <= 3:
                suggestions.append(Suggestion(
                    type=SuggestionType.LEARNING,
                    title="Get Started with Codexa",
                    description="Learn the basics of using Codexa effectively",
                    action="Run `/help` or try describing what you want to build",
                    priority=5,
                    context_match=0.9,
                    commands=["/help", "/status"],
                    examples=[
                        "Create a React login component",
                        "Build a Python REST API",
                        "Help me debug this error"
                    ],
                    benefits=[
                        "Understand Codexa capabilities",
                        "Learn command shortcuts",
                        "Discover advanced features"
                    ]
                ))
            
            return suggestions
        
        def provider_optimization_suggestions(context: Dict[str, Any]) -> List[Suggestion]:
            """Suggestions for provider optimization."""
            suggestions = []
            
            if context.get("provider_issues", 0) > 2:
                suggestions.append(Suggestion(
                    type=SuggestionType.OPTIMIZATION,
                    title="Optimize AI Provider Performance",
                    description="Your current provider seems to have issues. Consider switching.",
                    action="Run `/provider list` and switch to a more reliable provider",
                    priority=4,
                    context_match=0.8,
                    commands=["/provider list", "/provider switch <name>"],
                    benefits=[
                        "Better response times",
                        "Higher success rates",
                        "More reliable service"
                    ]
                ))
            
            return suggestions
        
        def mcp_enhancement_suggestions(context: Dict[str, Any]) -> List[Suggestion]:
            """Suggestions for MCP enhancements."""
            suggestions = []
            
            if context.get("mcp_servers_enabled", 0) == 0:
                suggestions.append(Suggestion(
                    type=SuggestionType.FEATURE,
                    title="Enhance with MCP Servers",
                    description="Enable MCP servers for specialized capabilities",
                    action="Try `/mcp enable context7` for documentation help",
                    priority=3,
                    context_match=0.7,
                    commands=["/mcp list", "/mcp enable <server>"],
                    examples=[
                        "/mcp enable context7 - Documentation lookup",
                        "/mcp enable sequential - Complex reasoning",
                        "/mcp enable magic - UI component generation"
                    ],
                    benefits=[
                        "Enhanced documentation lookup",
                        "Better code analysis",
                        "UI component generation",
                        "Cross-browser testing"
                    ]
                ))
            
            return suggestions
        
        def workflow_efficiency_suggestions(context: Dict[str, Any]) -> List[Suggestion]:
            """Suggestions for workflow efficiency."""
            suggestions = []
            
            recent_commands = context.get("recent_commands", [])
            if len(recent_commands) > 5:
                # Check for repetitive patterns
                command_counts = {}
                for cmd in recent_commands[-10:]:
                    command_counts[cmd] = command_counts.get(cmd, 0) + 1
                
                repeated_commands = [cmd for cmd, count in command_counts.items() if count > 2]
                
                if repeated_commands:
                    suggestions.append(Suggestion(
                        type=SuggestionType.WORKFLOW,
                        title="Optimize Your Workflow",
                        description="You're using some commands repeatedly. Consider automation.",
                        action="Create custom workflows or aliases for frequent tasks",
                        priority=2,
                        context_match=0.6,
                        benefits=[
                            "Save time on repetitive tasks",
                            "Reduce typing and errors",
                            "Streamline your workflow"
                        ],
                        estimated_time="5-10 minutes"
                    ))
            
            return suggestions
        
        def project_setup_suggestions(context: Dict[str, Any]) -> List[Suggestion]:
            """Suggestions for project setup."""
            suggestions = []
            
            project_type = context.get("project_type")
            if project_type:
                if project_type == "react" and not context.get("mcp_magic_enabled"):
                    suggestions.append(Suggestion(
                        type=SuggestionType.PROJECT_SETUP,
                        title="Enable React Component Generation",
                        description="Enable Magic MCP server for React component generation",
                        action="Run `/mcp enable magic` for UI component help",
                        priority=4,
                        context_match=0.8,
                        commands=["/mcp enable magic"],
                        benefits=[
                            "Generate React components",
                            "Responsive design patterns",
                            "Accessibility compliance"
                        ]
                    ))
                
                elif project_type == "python" and not context.get("mcp_sequential_enabled"):
                    suggestions.append(Suggestion(
                        type=SuggestionType.PROJECT_SETUP,
                        title="Enable Advanced Code Analysis",
                        description="Enable Sequential MCP server for better Python analysis",
                        action="Run `/mcp enable sequential` for enhanced reasoning",
                        priority=3,
                        context_match=0.7,
                        commands=["/mcp enable sequential"],
                        benefits=[
                            "Advanced code analysis",
                            "Complex reasoning",
                            "Better debugging help"
                        ]
                    ))
            
            return suggestions
        
        # Register suggestion rules
        self.suggestion_rules.extend([
            new_user_suggestions,
            provider_optimization_suggestions,
            mcp_enhancement_suggestions,
            workflow_efficiency_suggestions,
            project_setup_suggestions
        ])
    
    def _initialize_context_analyzers(self):
        """Initialize context analyzers."""
        
        def analyze_project_structure(context: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze project structure for suggestions."""
            analysis = {}
            
            files = context.get("project_files", [])
            
            # Detect project type
            if any(f.endswith(('.jsx', '.tsx')) for f in files):
                analysis["project_type"] = "react"
            elif any(f.endswith('.py') for f in files):
                analysis["project_type"] = "python"
            elif any(f.endswith('.js') for f in files):
                analysis["project_type"] = "nodejs"
            
            # Check for package.json, requirements.txt, etc.
            if "package.json" in files:
                analysis["has_package_json"] = True
            if "requirements.txt" in files:
                analysis["has_requirements"] = True
            
            return analysis
        
        def analyze_user_behavior(context: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze user behavior patterns."""
            analysis = {}
            
            recent_actions = context.get("recent_actions", [])
            if recent_actions:
                # Calculate session activity
                analysis["session_activity"] = len(recent_actions)
                
                # Find most common actions
                action_counts = {}
                for action in recent_actions[-20:]:
                    action_counts[action] = action_counts.get(action, 0) + 1
                
                most_common = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
                analysis["most_common_actions"] = most_common[:5]
            
            return analysis
        
        def analyze_error_patterns(context: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze error patterns for suggestions."""
            analysis = {}
            
            recent_errors = context.get("recent_errors", [])
            if recent_errors:
                # Group similar errors
                error_patterns = {}
                for error in recent_errors[-10:]:
                    # Simple pattern matching
                    if "provider" in error.lower():
                        error_patterns["provider_issues"] = error_patterns.get("provider_issues", 0) + 1
                    elif "mcp" in error.lower():
                        error_patterns["mcp_issues"] = error_patterns.get("mcp_issues", 0) + 1
                    elif "command" in error.lower():
                        error_patterns["command_issues"] = error_patterns.get("command_issues", 0) + 1
                
                analysis.update(error_patterns)
            
            return analysis
        
        # Register context analyzers
        self.context_analyzers.extend([
            analyze_project_structure,
            analyze_user_behavior,
            analyze_error_patterns
        ])
    
    def generate_suggestions(self, context: Dict[str, Any]) -> List[Suggestion]:
        """Generate contextual suggestions."""
        # Enhance context with analysis
        enhanced_context = context.copy()
        
        for analyzer in self.context_analyzers:
            try:
                analysis = analyzer(context)
                enhanced_context.update(analysis)
            except Exception as e:
                self.logger.error(f"Context analyzer error: {e}")
        
        # Generate suggestions using rules
        all_suggestions = []
        
        for rule in self.suggestion_rules:
            try:
                suggestions = rule(enhanced_context)
                all_suggestions.extend(suggestions)
            except Exception as e:
                self.logger.error(f"Suggestion rule error: {e}")
        
        # Sort by score and return top suggestions
        all_suggestions.sort()
        return all_suggestions[:8]  # Return top 8 suggestions
    
    def display_suggestions(self, suggestions: List[Suggestion], title: str = "💡 Suggestions"):
        """Display suggestions in a formatted way."""
        if not suggestions:
            return
        
        self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
        
        # Group suggestions by type
        type_groups = {}
        for suggestion in suggestions:
            type_name = suggestion.type.value.replace("_", " ").title()
            if type_name not in type_groups:
                type_groups[type_name] = []
            type_groups[type_name].append(suggestion)
        
        for type_name, group_suggestions in type_groups.items():
            self.console.print(f"\n[bold yellow]{type_name}:[/bold yellow]")
            
            for i, suggestion in enumerate(group_suggestions, 1):
                priority_indicator = "🔥" if suggestion.priority >= 4 else "⭐" if suggestion.priority >= 3 else "💡"
                
                panel_content = []
                panel_content.append(suggestion.description)
                panel_content.append(f"\n[bold green]Action:[/bold green] {suggestion.action}")
                
                if suggestion.benefits:
                    panel_content.append(f"\n[bold cyan]Benefits:[/bold cyan]")
                    for benefit in suggestion.benefits[:3]:
                        panel_content.append(f"• {benefit}")
                
                if suggestion.commands:
                    panel_content.append(f"\n[dim]Commands: {', '.join(suggestion.commands)}[/dim]")
                
                panel = Panel(
                    "\n".join(panel_content),
                    title=f"{priority_indicator} {suggestion.title}",
                    border_style="blue" if suggestion.priority >= 4 else "yellow",
                    padding=(0, 1)
                )
                
                self.console.print(panel)
    
    def record_user_action(self, action: str, context: Optional[Dict[str, Any]] = None):
        """Record user action for behavior analysis."""
        self.user_actions.append((action, datetime.now()))
        
        # Keep only recent actions (last 100)
        self.user_actions = self.user_actions[-100:]
        
        # Update context if provided
        if context:
            self.project_context.update(context)
    
    def get_quick_suggestions(self, current_input: str, context: Dict[str, Any]) -> List[str]:
        """Get quick suggestions for current input."""
        suggestions = []
        
        input_lower = current_input.lower()
        
        # Command completion
        if current_input.startswith('/'):
            from ..commands.command_registry import CommandRegistry
            # This would need access to the command registry
            # For now, provide common completions
            common_commands = [
                "/help", "/status", "/provider", "/model", "/mcp", 
                "/commands", "/config"
            ]
            
            partial_cmd = current_input[1:]
            matching = [cmd for cmd in common_commands if cmd[1:].startswith(partial_cmd)]
            suggestions.extend(matching[:5])
        
        # Natural language suggestions
        else:
            if len(current_input) > 10:  # Only for substantial input
                if any(word in input_lower for word in ["create", "build", "make"]):
                    suggestions.extend([
                        "Create a React component",
                        "Build a REST API",
                        "Make a config file"
                    ])
                elif any(word in input_lower for word in ["help", "how"]):
                    suggestions.extend([
                        "Use /help for commands",
                        "Try /status to check system",
                        "Use /mcp list for servers"
                    ])
        
        return suggestions[:3]  # Return top 3
    
    def update_user_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences for better suggestions."""
        self.user_preferences.update(preferences)
    
    def get_suggestion_analytics(self) -> Dict[str, Any]:
        """Get analytics on suggestion effectiveness."""
        recent_actions = [action for action, timestamp in self.user_actions 
                         if (datetime.now() - timestamp).hours < 24]
        
        return {
            "total_actions": len(self.user_actions),
            "recent_actions": len(recent_actions),
            "user_preferences": self.user_preferences,
            "project_context": self.project_context
        }
    
    def add_suggestion_rule(self, rule_func: callable):
        """Add custom suggestion rule."""
        self.suggestion_rules.append(rule_func)
    
    def add_context_analyzer(self, analyzer_func: callable):
        """Add custom context analyzer."""
        self.context_analyzers.append(analyzer_func)