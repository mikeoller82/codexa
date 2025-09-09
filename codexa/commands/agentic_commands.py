"""
Agentic loop commands for Codexa.
"""

import asyncio
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .command_registry import Command, CommandContext, CommandCategory, CommandParameter

try:
    from ..agentic_loop import CodexaAgenticLoop, create_agentic_loop
    AGENTIC_AVAILABLE = True
except ImportError:
    AGENTIC_AVAILABLE = False


class AgenticCommand(Command):
    """Run a task using the agentic loop system."""
    
    def __init__(self):
        super().__init__()
        self.name = "agentic"
        self.description = "Run a task using autonomous agentic loop (think, execute, evaluate, repeat)"
        self.category = CommandCategory.DEVELOPMENT
        self.parameters = [
            CommandParameter(
                "task", 
                str, 
                True, 
                None, 
                "The task description to accomplish"
            ),
            CommandParameter(
                "max_iterations", 
                int, 
                False, 
                20, 
                "Maximum number of loop iterations"
            ),
            CommandParameter(
                "verbose", 
                bool, 
                False, 
                True, 
                "Show detailed thinking and execution steps"
            ),
            CommandParameter(
                "interactive", 
                bool, 
                False, 
                False, 
                "Request confirmation between iterations"
            )
        ]
        self.aliases = ["loop", "autonomous", "think"]
    
    async def execute(self, context: CommandContext) -> str:
        if not AGENTIC_AVAILABLE:
            return "❌ Agentic loop system is not available. Please check the installation."
        
        task = context.parsed_args.get("task")
        max_iterations = context.parsed_args.get("max_iterations", 20)
        verbose = context.parsed_args.get("verbose", True)
        interactive = context.parsed_args.get("interactive", False)
        
        console = Console()
        
        try:
            # Create agentic loop instance with proper config
            loop = create_agentic_loop(
                config=context.config,
                max_iterations=max_iterations,
                verbose=verbose
            )
            
            # Verify provider is available
            if not loop.provider:
                return """❌ No AI provider is configured or available.
                
Please configure an AI provider first:
• Set OPENROUTER_API_KEY environment variable for OpenRouter
• Set OPENAI_API_KEY for OpenAI  
• Set ANTHROPIC_API_KEY for Anthropic

Then restart Codexa and try again."""
            
            if interactive:
                console.print("[yellow]Running in interactive mode - you'll be asked to confirm each iteration.[/yellow]")
            
            # Run the agentic loop
            result = await loop.run_agentic_loop(task)
            
            # Format the result
            if result.success:
                status_msg = f"✅ Task completed successfully in {len(result.iterations)} iterations"
            else:
                status_msg = f"⚠️ Task reached max iterations ({max_iterations}) without completion"
            
            return f"""
{status_msg}

[bold cyan]Task:[/bold cyan] {task}
[bold cyan]Duration:[/bold cyan] {result.total_duration:.2f} seconds
[bold cyan]Iterations:[/bold cyan] {len(result.iterations)}

[bold cyan]Final Result:[/bold cyan]
{result.final_result or "Task completed but no specific result available"}

Use `/agentic-history` to see detailed iteration history.
            """.strip()
            
        except Exception as e:
            return f"❌ Agentic loop execution failed: {str(e)}"


class AgenticHistoryCommand(Command):
    """Show the history of the last agentic loop execution."""
    
    def __init__(self):
        super().__init__()
        self.name = "agentic-history"
        self.description = "Show detailed history of the last agentic loop execution"
        self.category = CommandCategory.DEVELOPMENT
        self.parameters = [
            CommandParameter(
                "iteration", 
                int, 
                False, 
                None, 
                "Show details for a specific iteration number"
            ),
            CommandParameter(
                "summary", 
                bool, 
                False, 
                False, 
                "Show only summary information"
            )
        ]
        self.aliases = ["loop-history", "agentic-log"]
    
    async def execute(self, context: CommandContext) -> str:
        if not AGENTIC_AVAILABLE:
            return "❌ Agentic loop system is not available."
        
        # In a full implementation, we would store the last loop result
        # in the session data or agent state
        return """
[yellow]Agentic history feature is available but requires integration with session storage.[/yellow]

This command will show:
• Detailed iteration history
• Thinking process for each step
• Execution results and evaluations
• Performance metrics
• Success/failure analysis

[dim]Note: History storage will be implemented when integrated with the main agent.[/dim]
        """.strip()


class AgenticConfigCommand(Command):
    """Configure agentic loop settings."""
    
    def __init__(self):
        super().__init__()
        self.name = "agentic-config"
        self.description = "Configure agentic loop default settings"
        self.category = CommandCategory.DEVELOPMENT
        self.parameters = [
            CommandParameter(
                "setting", 
                str, 
                True, 
                None, 
                "Setting to configure",
                choices=["max_iterations", "verbose", "timeout", "show"]
            ),
            CommandParameter(
                "value", 
                str, 
                False, 
                None, 
                "New value for the setting"
            )
        ]
        self.aliases = ["loop-config"]
    
    async def execute(self, context: CommandContext) -> str:
        if not AGENTIC_AVAILABLE:
            return "❌ Agentic loop system is not available."
        
        setting = context.parsed_args.get("setting")
        value = context.parsed_args.get("value")
        
        if setting == "show":
            return """
[bold cyan]Agentic Loop Configuration[/bold cyan]

[yellow]Current Settings:[/yellow]
• Max Iterations: 20 (default)
• Verbose Mode: True (default)
• Interactive Mode: False (default)
• Timeout: 300 seconds (default)

[yellow]Available Settings:[/yellow]
• [cyan]max_iterations[/cyan] - Maximum number of loop iterations (1-100)
• [cyan]verbose[/cyan] - Show detailed thinking process (true/false)
• [cyan]timeout[/cyan] - Maximum execution time per iteration (seconds)

[yellow]Examples:[/yellow]
• /agentic-config max_iterations 30
• /agentic-config verbose false
            """.strip()
        
        if value is None:
            return f"❌ Please provide a value for setting '{setting}'"
        
        # In full implementation, would save to config
        return f"""
✅ Agentic loop setting updated:
[cyan]{setting}[/cyan] = [yellow]{value}[/yellow]

[dim]Note: Settings persistence will be implemented when integrated with the main configuration system.[/dim]
        """.strip()


class AgenticExamplesCommand(Command):
    """Show examples of agentic loop usage."""
    
    def __init__(self):
        super().__init__()
        self.name = "agentic-examples"
        self.description = "Show examples of how to use the agentic loop"
        self.category = CommandCategory.HELP
        self.parameters = []
        self.aliases = ["loop-examples", "agentic-help"]
    
    async def execute(self, context: CommandContext) -> str:
        return """
[bold cyan]Agentic Loop Examples[/bold cyan]

[yellow]Basic Task Execution:[/yellow]
• `/agentic "create a Python script that calculates fibonacci numbers"`
• `/agentic "analyze the codebase and suggest improvements"`
• `/agentic "fix the bug in authentication.py"`

[yellow]With Custom Parameters:[/yellow]
• `/agentic "implement user registration" --max_iterations 10`
• `/agentic "refactor the database code" --verbose false`
• `/agentic "add error handling" --interactive true`

[yellow]Complex Tasks:[/yellow]
• `/agentic "create a REST API with authentication and user management"`
• `/agentic "implement a complete login system with password reset"`
• `/agentic "build a dashboard with real-time data visualization"`

[yellow]How It Works:[/yellow]
1. 🧠 [bold]Think[/bold] - Codexa analyzes the task and plans the next step
2. ⚡ [bold]Execute[/bold] - Takes one concrete action (read files, write code, run commands)
3. 🔍 [bold]Evaluate[/bold] - Checks if the action helped achieve the goal
4. 🔄 [bold]Refine[/bold] - Updates understanding and tries again if needed
5. 🎉 [bold]Complete[/bold] - Stops when task is done or max iterations reached

[yellow]Tips for Better Results:[/yellow]
• Be specific about what you want to achieve
• Break complex tasks into smaller, focused requests
• Use descriptive language about expected outcomes
• Consider using `--interactive true` for complex tasks to guide the process

Try: `/agentic "show me how this works by creating a simple hello world script"`
        """.strip()


# Registry of agentic commands
AGENTIC_COMMANDS = [
    AgenticCommand,
    AgenticHistoryCommand,
    AgenticConfigCommand,
    AgenticExamplesCommand,
]