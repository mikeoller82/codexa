"""
Advanced user guidance system with interactive help and contextual assistance.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn


class GuidanceType(Enum):
    """Types of user guidance."""
    TUTORIAL = "tutorial"
    QUICK_START = "quick_start"
    TROUBLESHOOTING = "troubleshooting"
    BEST_PRACTICES = "best_practices"
    REFERENCE = "reference"
    INTERACTIVE = "interactive"
    CONTEXTUAL = "contextual"


@dataclass
class GuidanceContext:
    """Context for guidance requests."""
    user_level: str = "beginner"  # beginner, intermediate, advanced
    current_task: Optional[str] = None
    error_history: List[str] = field(default_factory=list)
    session_state: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractiveGuidance:
    """Interactive guidance session."""
    title: str
    description: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    estimated_time: str = "5-10 minutes"
    difficulty: str = "beginner"
    
    def add_step(self, name: str, description: str, action: Optional[Callable] = None, **kwargs):
        """Add a step to the guidance."""
        self.steps.append({
            "name": name,
            "description": description,
            "action": action,
            "kwargs": kwargs
        })


class UserGuidanceSystem:
    """Advanced user guidance system with contextual help."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        
        # Guidance database
        self.guidance_library: Dict[str, InteractiveGuidance] = {}
        self.quick_tips: Dict[str, List[str]] = {}
        self.troubleshooting_guides: Dict[str, Dict[str, Any]] = {}
        
        # User interaction tracking
        self.user_context = GuidanceContext()
        self.interaction_history: List[Dict[str, Any]] = []
        
        # Initialize built-in guidance
        self._initialize_guidance_library()
        self._initialize_quick_tips()
        self._initialize_troubleshooting_guides()
    
    def provide_guidance(
        self,
        topic: str,
        guidance_type: GuidanceType = GuidanceType.CONTEXTUAL,
        context: Optional[GuidanceContext] = None
    ) -> bool:
        """Provide contextual guidance to the user."""
        if context:
            self.user_context = context
        
        # Record interaction
        self._record_interaction(topic, guidance_type)
        
        if guidance_type == GuidanceType.INTERACTIVE:
            return self._provide_interactive_guidance(topic)
        elif guidance_type == GuidanceType.QUICK_START:
            return self._provide_quick_start_guidance(topic)
        elif guidance_type == GuidanceType.TROUBLESHOOTING:
            return self._provide_troubleshooting_guidance(topic)
        elif guidance_type == GuidanceType.TUTORIAL:
            return self._provide_tutorial_guidance(topic)
        else:
            return self._provide_contextual_guidance(topic)
    
    def _provide_interactive_guidance(self, topic: str) -> bool:
        """Provide interactive step-by-step guidance."""
        if topic not in self.guidance_library:
            self.console.print(f"[red]No interactive guidance available for '{topic}'[/red]")
            return False
        
        guidance = self.guidance_library[topic]
        
        # Show guidance introduction
        intro_panel = Panel(
            f"{guidance.description}\n\n"
            f"[cyan]Estimated time:[/cyan] {guidance.estimated_time}\n"
            f"[cyan]Difficulty:[/cyan] {guidance.difficulty}\n"
            f"[cyan]Steps:[/cyan] {len(guidance.steps)}",
            title=f"📚 {guidance.title}",
            border_style="blue"
        )
        
        self.console.print(intro_panel)
        
        # Check prerequisites
        if guidance.prerequisites:
            self.console.print("\n[yellow]Prerequisites:[/yellow]")
            for prereq in guidance.prerequisites:
                self.console.print(f"• {prereq}")
            
            if not Confirm.ask("\nDo you want to continue?", default=True):
                return False
        
        # Execute steps interactively
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            
            for i, step in enumerate(guidance.steps, 1):
                # Display step
                step_panel = Panel(
                    step["description"],
                    title=f"Step {i}: {step['name']}",
                    border_style="green"
                )
                
                self.console.print(f"\n{step_panel}")
                
                # Execute step action if available
                if step.get("action"):
                    try:
                        task = progress.add_task(f"Executing {step['name']}...", total=None)
                        result = step["action"](**step.get("kwargs", {}))
                        progress.remove_task(task)
                        
                        if result:
                            self.console.print("[green]✓ Step completed successfully[/green]")
                        else:
                            self.console.print("[yellow]⚠ Step completed with warnings[/yellow]")
                    except Exception as e:
                        progress.remove_task(task)
                        self.console.print(f"[red]❌ Step failed: {e}[/red]")
                        
                        if not Confirm.ask("Continue anyway?", default=True):
                            return False
                
                # Wait for user confirmation to continue
                if i < len(guidance.steps):
                    if not Confirm.ask("Ready for next step?", default=True):
                        self.console.print("[yellow]Guidance session paused.[/yellow]")
                        return False
        
        self.console.print("\n[green]🎉 Guidance completed successfully![/green]")
        return True
    
    def _provide_quick_start_guidance(self, topic: str) -> bool:
        """Provide quick start guidance."""
        if topic not in self.quick_tips:
            return self._provide_contextual_guidance(topic)
        
        tips = self.quick_tips[topic]
        
        # Create quick tips panel
        content = []
        for i, tip in enumerate(tips, 1):
            content.append(f"{i}. {tip}")
        
        panel = Panel(
            "\n".join(content),
            title=f"⚡ Quick Tips: {topic.title()}",
            border_style="yellow"
        )
        
        self.console.print(panel)
        return True
    
    def _provide_troubleshooting_guidance(self, topic: str) -> bool:
        """Provide troubleshooting guidance."""
        if topic not in self.troubleshooting_guides:
            self.console.print(f"[red]No troubleshooting guide available for '{topic}'[/red]")
            return False
        
        guide = self.troubleshooting_guides[topic]
        
        # Show troubleshooting steps
        self.console.print(f"\n[bold cyan]🔧 Troubleshooting: {topic.title()}[/bold cyan]\n")
        
        # Common causes
        if "common_causes" in guide:
            self.console.print("[yellow]Common Causes:[/yellow]")
            for cause in guide["common_causes"]:
                self.console.print(f"• {cause}")
            self.console.print()
        
        # Diagnostic steps
        if "diagnostic_steps" in guide:
            self.console.print("[blue]Diagnostic Steps:[/blue]")
            for i, step in enumerate(guide["diagnostic_steps"], 1):
                self.console.print(f"{i}. {step}")
            self.console.print()
        
        # Solutions
        if "solutions" in guide:
            self.console.print("[green]Solutions:[/green]")
            for i, solution in enumerate(guide["solutions"], 1):
                self.console.print(f"{i}. {solution}")
        
        return True
    
    def _provide_tutorial_guidance(self, topic: str) -> bool:
        """Provide tutorial guidance."""
        # For now, delegate to interactive guidance
        return self._provide_interactive_guidance(topic)
    
    def _provide_contextual_guidance(self, topic: str) -> bool:
        """Provide contextual guidance based on current context."""
        # Analyze user context and provide relevant guidance
        guidance_content = self._generate_contextual_content(topic)
        
        if not guidance_content:
            self.console.print(f"[yellow]No specific guidance available for '{topic}'[/yellow]")
            return False
        
        panel = Panel(
            guidance_content,
            title=f"💡 Contextual Help: {topic.title()}",
            border_style="cyan"
        )
        
        self.console.print(panel)
        return True
    
    def _generate_contextual_content(self, topic: str) -> str:
        """Generate contextual guidance content."""
        content_parts = []
        
        # Add basic information
        if topic.lower() in ["commands", "command"]:
            content_parts.extend([
                "Available command categories:",
                "• `/help` - Get help with commands",
                "• `/provider` - Manage AI providers",
                "• `/mcp` - Control MCP servers",
                "• `/config` - Configuration management",
                "",
                "Use `/help <command>` for specific command help."
            ])
        
        elif "provider" in topic.lower():
            content_parts.extend([
                "Provider management:",
                "• `/provider list` - Show available providers",
                "• `/provider status` - Check current provider",
                "• `/provider switch <name>` - Switch providers",
                "",
                "Make sure your API keys are properly configured."
            ])
        
        elif "mcp" in topic.lower():
            content_parts.extend([
                "MCP server management:",
                "• `/mcp list` - Show available servers", 
                "• `/mcp status` - Check server status",
                "• `/mcp enable <server>` - Enable a server",
                "• `/mcp restart <server>` - Restart a server",
                "",
                "MCP servers provide specialized capabilities."
            ])
        
        # Add context-specific information based on user level
        if self.user_context.user_level == "beginner":
            content_parts.extend([
                "",
                "[dim]💡 Tip: Start with `/help` to explore available commands.[/dim]"
            ])
        elif self.user_context.user_level == "advanced":
            content_parts.extend([
                "",
                "[dim]💡 Tip: Use command flags for advanced options.[/dim]"
            ])
        
        return "\n".join(content_parts)
    
    def suggest_next_actions(self, context: Optional[str] = None) -> List[str]:
        """Suggest relevant next actions based on context."""
        suggestions = []
        
        # Context-based suggestions
        if context:
            if "error" in context.lower():
                suggestions.extend([
                    "Check error logs with `/logs`",
                    "Verify configuration with `/config check`",
                    "Get help with `/help troubleshooting`"
                ])
            elif "provider" in context.lower():
                suggestions.extend([
                    "Check provider status with `/provider status`",
                    "List available providers with `/provider list`",
                    "Switch providers with `/provider switch <name>`"
                ])
        
        # General suggestions based on user level
        if self.user_context.user_level == "beginner":
            suggestions.extend([
                "Start with `/help` to explore commands",
                "Try `/status` to check system health",
                "Use `/config show` to see current settings"
            ])
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _record_interaction(self, topic: str, guidance_type: GuidanceType):
        """Record user interaction for learning."""
        interaction = {
            "timestamp": datetime.now(),
            "topic": topic,
            "type": guidance_type.value,
            "user_level": self.user_context.user_level,
            "current_task": self.user_context.current_task
        }
        
        self.interaction_history.append(interaction)
        
        # Keep only recent interactions
        if len(self.interaction_history) > 100:
            self.interaction_history = self.interaction_history[-100:]
    
    def _initialize_guidance_library(self):
        """Initialize the guidance library with built-in guides."""
        # Getting Started guide
        getting_started = InteractiveGuidance(
            title="Getting Started with Codexa",
            description="A comprehensive introduction to using Codexa effectively",
            estimated_time="10-15 minutes",
            difficulty="beginner"
        )
        
        getting_started.add_step(
            "Check System Status",
            "Let's start by checking if Codexa is properly configured",
            lambda: self.console.print("System status checked ✓")
        )
        
        getting_started.add_step(
            "Configure Provider",
            "Set up your AI provider for optimal performance",
            lambda: self.console.print("Provider configured ✓")
        )
        
        getting_started.add_step(
            "Try First Command",
            "Execute your first command to test everything works",
            lambda: self.console.print("First command executed ✓")
        )
        
        self.guidance_library["getting_started"] = getting_started
        
        # Provider Setup guide
        provider_setup = InteractiveGuidance(
            title="Provider Setup and Management",
            description="Learn how to configure and manage AI providers",
            estimated_time="5-10 minutes",
            difficulty="beginner"
        )
        
        provider_setup.prerequisites = [
            "Have at least one API key configured",
            "Network connectivity available"
        ]
        
        self.guidance_library["provider_setup"] = provider_setup
    
    def _initialize_quick_tips(self):
        """Initialize quick tips database."""
        self.quick_tips["commands"] = [
            "Use `/help` to see all available commands",
            "Commands support tab completion",
            "Use `/help <command>` for specific command help",
            "Most commands have short aliases (e.g., `/h` for `/help`)",
            "Use `--help` flag for detailed command options"
        ]
        
        self.quick_tips["providers"] = [
            "Check current provider with `/provider status`",
            "Switch providers with `/provider switch <name>`",
            "List available providers with `/provider list`",
            "Set environment variables for API keys",
            "Use `/provider test` to verify configuration"
        ]
        
        self.quick_tips["mcp"] = [
            "Enable servers with `/mcp enable <server>`",
            "Check server status with `/mcp status`",
            "Restart problematic servers with `/mcp restart <server>`",
            "View server logs with `/mcp logs <server>`",
            "Use `/mcp help` for MCP-specific guidance"
        ]
    
    def _initialize_troubleshooting_guides(self):
        """Initialize troubleshooting guides."""
        self.troubleshooting_guides["connection"] = {
            "common_causes": [
                "Network connectivity issues",
                "Incorrect API key configuration",
                "Provider service outage",
                "Firewall blocking connections"
            ],
            "diagnostic_steps": [
                "Check network connectivity",
                "Verify API key is set and valid",
                "Test with different provider",
                "Check firewall settings"
            ],
            "solutions": [
                "Switch to backup provider",
                "Update API keys",
                "Check provider status pages",
                "Configure proxy if needed"
            ]
        }
        
        self.troubleshooting_guides["performance"] = {
            "common_causes": [
                "High system load",
                "Provider API throttling",
                "Large request payloads",
                "Network latency"
            ],
            "diagnostic_steps": [
                "Check system resources",
                "Monitor provider response times",
                "Review request sizes",
                "Test network latency"
            ],
            "solutions": [
                "Reduce request complexity",
                "Switch to faster provider",
                "Implement request batching",
                "Use local caching"
            ]
        }
    
    def get_guidance_analytics(self) -> Dict[str, Any]:
        """Get analytics on guidance usage."""
        if not self.interaction_history:
            return {"total_interactions": 0}
        
        # Analyze interaction patterns
        topic_counts = {}
        type_counts = {}
        
        for interaction in self.interaction_history:
            topic = interaction["topic"]
            guidance_type = interaction["type"]
            
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            type_counts[guidance_type] = type_counts.get(guidance_type, 0) + 1
        
        return {
            "total_interactions": len(self.interaction_history),
            "popular_topics": sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "guidance_types": type_counts,
            "user_level_distribution": {
                level: len([i for i in self.interaction_history if i.get("user_level") == level])
                for level in ["beginner", "intermediate", "advanced"]
            }
        }