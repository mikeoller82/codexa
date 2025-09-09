"""
KillBash tool - Kills a running background bash shell by its ID.
"""

from typing import Set
from ..base.tool_interface import Tool, ToolContext, ToolResult


class KillBashTool(Tool):
    """Kills a running background bash shell by its ID."""
    
    @property
    def name(self) -> str:
        return "KillBash"
    
    @property
    def description(self) -> str:
        return "Kills a running background bash shell by its ID"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"shell_id"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit kill requests
        if any(phrase in request_lower for phrase in [
            "kill bash", "kill shell", "terminate shell", "stop background"
        ]):
            return 0.9
        
        # Medium confidence for general termination
        if any(phrase in request_lower for phrase in [
            "kill", "terminate", "stop", "cancel"
        ]) and any(phrase in request_lower for phrase in [
            "background", "shell", "process", "command"
        ]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the KillBash tool."""
        try:
            # Extract parameters
            shell_id = context.get_state("shell_id")
            
            if not shell_id:
                return ToolResult.error_result(
                    error="Missing required parameter: shell_id",
                    tool_name=self.name
                )
            
            # Try to get the BashTool instance from tool manager
            bash_tool = None
            if context.tool_manager:
                bash_tool = context.tool_manager.registry.get_tool("Bash")
            
            if not bash_tool:
                return ToolResult.error_result(
                    error="BashTool not available for shell termination",
                    tool_name=self.name
                )
            
            # Kill the background shell
            result = bash_tool.kill_background_shell(shell_id)
            
            if "error" in result:
                return ToolResult.error_result(
                    error=result["error"],
                    tool_name=self.name
                )
            
            return ToolResult.success_result(
                data={
                    "shell_id": shell_id,
                    "status": "terminated"
                },
                tool_name=self.name,
                output=result.get("message", f"Shell {shell_id} terminated successfully")
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"KillBash tool execution failed: {str(e)}",
                tool_name=self.name
            )


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "shell_id": {
            "type": "string",
            "description": "The ID of the background shell to kill"
        }
    },
    "required": ["shell_id"],
    "additionalProperties": False
}