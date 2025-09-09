"""
Enhanced agents command for Codexa - activates verbose agentic mode.
"""

import asyncio
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from .command_registry import Command, CommandContext, CommandCategory, CommandParameter

console = Console()


class AgentsCommand(Command):
    """Activate enhanced agents with verbose agentic loop and real-time feedback."""
    
    def __init__(self):
        super().__init__()
        self.name = "agents"
        self.description = "Activate all available agents with verbose agentic loop and real-time feedback"
        self.category = CommandCategory.DEVELOPMENT
        self.parameters = [
            CommandParameter(
                "task", 
                str, 
                True, 
                None, 
                "The task to execute using all available agents"
            ),
            CommandParameter(
                "max_iterations", 
                int, 
                False, 
                25, 
                "Maximum number of agentic loop iterations"
            ),
            CommandParameter(
                "show_tools", 
                bool, 
                False, 
                True, 
                "Show real-time tool selection and coordination"
            ),
            CommandParameter(
                "interactive", 
                bool, 
                False, 
                False, 
                "Require confirmation between iterations"
            )
        ]
        self.aliases = ["all-agents", "full-agents", "enhanced-agents"]
    
    async def execute(self, context: CommandContext) -> str:
        task = context.parsed_args.get("task")
        max_iterations = context.parsed_args.get("max_iterations", 25)
        show_tools = context.parsed_args.get("show_tools", True)
        interactive = context.parsed_args.get("interactive", False)
        
        try:
            # Show activation message
            console.print("\n[bold cyan]🚀 ENHANCED AGENTS ACTIVATED[/bold cyan]")
            console.print("[dim]Initializing verbose agentic loop with tool coordination...[/dim]\n")
            
            # Import and create enhanced agentic loop
            from ..agentic_loop import create_agentic_loop
            from ..tools.base.tool_interface import ToolContext
            
            # Create agentic loop with enhanced settings
            loop = create_agentic_loop(
                config=context.config,
                max_iterations=max_iterations,
                verbose=True  # Always verbose for agents command
            )
            
            # Ensure tool manager is available
            if hasattr(context, 'tool_manager') and context.tool_manager:
                loop.tool_manager = context.tool_manager
                console.print(f"[green]✅ Tool Manager: {len(loop.tool_manager.get_available_tools())} tools available[/green]")
            else:
                console.print("[yellow]⚠️ Tool Manager not available - using basic execution[/yellow]")
            
            # Set MCP service if available
            if hasattr(context, 'mcp_service') and context.mcp_service:
                loop.mcp_service = context.mcp_service
                console.print("[green]✅ MCP Service: Available for enhanced capabilities[/green]")
            
            # Verify provider
            if not loop.provider:
                return """❌ No AI provider configured for enhanced agents.
                
Please configure an API key:
• export OPENROUTER_API_KEY="your-key" (recommended)
• export OPENAI_API_KEY="your-key"  
• export ANTHROPIC_API_KEY="your-key"

Then restart Codexa and run: /agents "your task here"
"""
            
            provider_name = getattr(loop.provider, 'name', 'Unknown')
            console.print(f"[green]✅ AI Provider: {provider_name}[/green]")
            
            if show_tools:
                console.print("[green]✅ Real-time tool feedback: Enabled[/green]")
            
            if interactive:
                console.print("[yellow]ℹ️ Interactive mode: Will pause between iterations[/yellow]")
            
            console.print(f"[green]✅ Max iterations: {max_iterations}[/green]")
            console.print()
            
            # Show task overview
            console.print(Panel(
                f"[bold]Task:[/bold] {task}\n\n"
                f"[dim]The enhanced agents will:[/dim]\n"
                f"[dim]• Think through the problem step by step[/dim]\n"
                f"[dim]• Execute actions using available tools[/dim]\n"
                f"[dim]• Evaluate progress after each step[/dim]\n"
                f"[dim]• Iterate until completion or max iterations[/dim]\n"
                f"[dim]• Show all reasoning and tool usage in real-time[/dim]",
                title="🎯 Enhanced Agent Mission",
                title_align="left",
                border_style="blue",
                padding=(1, 2)
            ))
            
            if interactive and not Confirm.ask("\n[bold yellow]Ready to begin enhanced agent execution?[/bold yellow]"):
                return "❌ Enhanced agent execution cancelled."
            
            # Execute the agentic loop
            console.print("\n" + "="*80)
            console.print("[bold blue]🤖 ENHANCED AGENTS STARTING EXECUTION[/bold blue]")
            console.print("="*80)
            
            result = await loop.run_agentic_loop(task)
            
            # Format comprehensive results
            status_emoji = "🎉" if result.success else "⚠️"
            status_text = "SUCCESS" if result.success else "INCOMPLETE"
            
            summary = f"""
{status_emoji} **ENHANCED AGENTS EXECUTION {status_text}**

[bold cyan]Task Completed:[/bold cyan] {task}
[bold cyan]Final Status:[/bold cyan] {result.status.value}
[bold cyan]Iterations Used:[/bold cyan] {len(result.iterations)} of {max_iterations}
[bold cyan]Total Duration:[/bold cyan] {result.total_duration:.1f} seconds
[bold cyan]Success Rate:[/bold cyan] {result.success}

[bold cyan]Final Result:[/bold cyan]
{result.final_result or "Task execution completed - see iteration details above for full results"}

[bold cyan]Agent Performance:[/bold cyan]
• Average time per iteration: {result.total_duration / max(len(result.iterations), 1):.1f}s
• Thinking depth: {"High" if any(len(i.thinking) > 200 for i in result.iterations) else "Moderate"}
• Tool integration: {"Active" if hasattr(loop, 'tool_manager') and loop.tool_manager else "Basic"}

Use `/agentic-history` to see detailed iteration breakdown.
            """.strip()
            
            return summary
            
        except ImportError:
            return """❌ Enhanced agentic loop not available.
            
This may be due to missing dependencies. Please check:
• Rich console library
• Async capabilities
• Tool system components

Try running: pip install -e ".[dev]" """
            
        except Exception as e:
            console.print(f"[red]❌ Enhanced agents execution failed: {e}[/red]")
            return f"Enhanced agents execution failed: {str(e)}"


# Register the command
AGENTS_COMMANDS = [
    AgentsCommand,
]