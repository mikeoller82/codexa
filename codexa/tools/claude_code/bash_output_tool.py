"""
BashOutput tool - Retrieves output from a running or completed background bash shell.
"""

from typing import Set, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class BashOutputTool(Tool):
    """Retrieves output from a running or completed background bash shell."""
    
    @property
    def name(self) -> str:
        return "BashOutput"
    
    @property
    def description(self) -> str:
        return "Retrieves output from a running or completed background bash shell"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"bash_id"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit background output requests
        if any(phrase in request_lower for phrase in [
            "bash output", "background output", "shell output", "get output"
        ]):
            return 0.9
        
        # Medium confidence for background monitoring
        if any(phrase in request_lower for phrase in [
            "check background", "monitor", "status", "running command"
        ]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the BashOutput tool."""
        try:
            # Extract parameters
            bash_id = context.get_state("bash_id")
            filter_pattern = context.get_state("filter")
            
            if not bash_id:
                return ToolResult.error_result(
                    error="Missing required parameter: bash_id",
                    tool_name=self.name
                )
            
            # Try to get the BashTool instance from tool manager
            bash_tool = None
            if context.tool_manager:
                bash_tool = context.tool_manager.registry.get_tool("Bash")
            
            if not bash_tool:
                return ToolResult.error_result(
                    error="BashTool not available for background output retrieval",
                    tool_name=self.name
                )
            
            # Get output from bash tool
            output_data = bash_tool.get_background_output(bash_id, filter_pattern)
            
            if "error" in output_data:
                return ToolResult.error_result(
                    error=output_data["error"],
                    tool_name=self.name
                )
            
            # Format output
            if output_data.get("completed"):
                status = "completed"
                stdout = output_data.get("stdout", "")
                stderr = output_data.get("stderr", "")
                return_code = output_data.get("return_code", 0)
                
                output_text = ""
                if stdout:
                    output_text += f"STDOUT:\n{stdout}"
                if stderr:
                    if output_text:
                        output_text += "\n\n"
                    output_text += f"STDERR:\n{stderr}"
                
                output_text += f"\n\nExit Code: {return_code}"
                
            else:
                status = "running"
                output_text = output_data.get("output", "Process still running...")
            
            return ToolResult.success_result(
                data={
                    "bash_id": bash_id,
                    "status": status,
                    "output_data": output_data
                },
                tool_name=self.name,
                output=output_text
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"BashOutput tool execution failed: {str(e)}",
                tool_name=self.name
            )


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "bash_id": {
            "type": "string",
            "description": "The ID of the background shell to retrieve output from"
        },
        "filter": {
            "type": "string",
            "description": "Optional regular expression to filter the output lines"
        }
    },
    "required": ["bash_id"],
    "additionalProperties": False
}