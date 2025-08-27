"""
Autonomous mode commands for Codexa.
"""

from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .command_registry import Command, CommandRegistry, CommandCategory
from ..autonomous_agent import PermissionMode

console = Console()


class AutonomousCommands:
    """Commands for managing autonomous mode."""
    
    @staticmethod
    def register_all(registry: CommandRegistry):
        """Register all autonomous mode commands."""
        # Create a custom command class for autonomous functionality
        class AutonomousCommand(Command):
            def __init__(self):
                super().__init__()
                self.name = "autonomous"
                self.description = "Configure autonomous mode settings"
                self.category = CommandCategory.CORE
                self.aliases = ["auto"]
            
            async def execute(self, context):
                # Parse arguments from user input
                args = context.parsed_args.get('args', [])
                if not args and context.user_input.strip():
                    # Parse from raw input if needed
                    parts = context.user_input.strip().split()[1:]  # Skip command name
                    args = parts
                
                # Call the handler
                result = await AutonomousCommands.handle_autonomous(
                    args, 
                    codexa_agent=context.codexa_agent
                )
                
                if result.get("success"):
                    return result.get("message", "Command executed successfully")
                else:
                    return f"Error: {result.get('error', 'Unknown error')}"
        
        registry.register(AutonomousCommand())
    
    @staticmethod
    async def handle_autonomous(args: List[str], **kwargs) -> Dict[str, any]:
        """Handle autonomous mode configuration."""
        try:
            codexa_agent = kwargs.get('codexa_agent')
            if not codexa_agent or not codexa_agent.autonomous_agent:
                return {
                    "success": False,
                    "error": "Autonomous agent not available"
                }
            
            autonomous_agent = codexa_agent.autonomous_agent
            
            if not args or args[0] == "status":
                return AutonomousCommands._show_status(autonomous_agent)
            
            elif args[0] == "enable":
                # Autonomous mode is always available, but can configure permission mode
                console.print("[green]✅ Autonomous mode is enabled by default for action-oriented requests[/green]")
                console.print("[dim]Use '/autonomous permission <mode>' to configure permission settings[/dim]")
                return {"success": True}
            
            elif args[0] == "disable":
                console.print("[yellow]⚠️  Autonomous mode cannot be fully disabled[/yellow]")
                console.print("[dim]It automatically activates for requests that warrant autonomous action[/dim]")
                console.print("[dim]You can set permission mode to 'ask' to control when actions are taken[/dim]")
                return {"success": True}
            
            elif args[0] == "permission" and len(args) > 1:
                return AutonomousCommands._handle_permission_mode(autonomous_agent, args[1])
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown autonomous command: {args[0]}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Autonomous command failed: {str(e)}"
            }
    
    @staticmethod
    def _show_status(autonomous_agent) -> Dict[str, any]:
        """Show autonomous mode status."""
        table = Table(title="🤖 Autonomous Mode Status", show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")
        
        # Permission mode
        permission_mode = autonomous_agent.permission_mode
        permission_desc = {
            PermissionMode.ASK_EACH_TIME: "Ask before each action",
            PermissionMode.SESSION_WIDE: "Approved for entire session",
            PermissionMode.AUTO_APPROVE: "Automatic approval (not recommended)"
        }
        
        table.add_row(
            "Permission Mode",
            permission_mode.value,
            permission_desc.get(permission_mode, "Unknown")
        )
        
        # Session approval status
        session_status = "Yes" if autonomous_agent.session_approved else "No"
        table.add_row(
            "Session Approved",
            session_status,
            "Whether actions are pre-approved for this session"
        )
        
        # MCP availability
        mcp_status = "Available" if autonomous_agent.mcp_filesystem and autonomous_agent.mcp_filesystem.is_server_available() else "Not Available"
        table.add_row(
            "MCP Filesystem",
            mcp_status,
            "Enhanced file operations via MCP"
        )
        
        console.print(table)
        
        # Show usage tips
        tips_panel = Panel(
            """💡 **Autonomous Mode Tips:**

• Autonomous mode activates automatically for action-oriented requests like:
  - "Fix the login bug in auth.py"
  - "Add error handling to the API endpoints"
  - "Update the CSS to make the buttons responsive"

• For questions and explanations, manual mode is used:
  - "How does the authentication system work?"
  - "Explain what this code does"

• Use `/autonomous permission session` to approve all actions for the session
• Use `/autonomous permission ask` to be asked before each action""",
            title="Usage Guide",
            border_style="blue"
        )
        console.print(tips_panel)
        
        return {"success": True}
    
    @staticmethod
    def _handle_permission_mode(autonomous_agent, mode_str: str) -> Dict[str, any]:
        """Handle permission mode changes."""
        mode_mapping = {
            "ask": PermissionMode.ASK_EACH_TIME,
            "each": PermissionMode.ASK_EACH_TIME,
            "session": PermissionMode.SESSION_WIDE,
            "auto": PermissionMode.AUTO_APPROVE
        }
        
        mode_str_lower = mode_str.lower()
        if mode_str_lower not in mode_mapping:
            return {
                "success": False,
                "error": f"Unknown permission mode: {mode_str}. Use: ask, session, or auto"
            }
        
        new_mode = mode_mapping[mode_str_lower]
        autonomous_agent.set_permission_mode(new_mode)
        
        mode_descriptions = {
            PermissionMode.ASK_EACH_TIME: "Ask before each action",
            PermissionMode.SESSION_WIDE: "Approve all actions for this session",
            PermissionMode.AUTO_APPROVE: "Automatically approve all actions (use with caution!)"
        }
        
        console.print(f"[green]✅ Permission mode set to: {new_mode.value}[/green]")
        console.print(f"[dim]{mode_descriptions[new_mode]}[/dim]")
        
        if new_mode == PermissionMode.AUTO_APPROVE:
            console.print("[bold red]⚠️  Warning: Auto-approve mode will execute actions without confirmation![/bold red]")
        
        return {"success": True}