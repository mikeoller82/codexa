"""
Task tool - Launch a new agent to handle complex, multi-step tasks autonomously.
"""

import json
import asyncio
from typing import Set, Dict, Any
from ..base.tool_interface import Tool, ToolContext, ToolResult


class TaskTool(Tool):
    """Launch a new agent to handle complex, multi-step tasks autonomously."""
    
    @property
    def name(self) -> str:
        return "Task"
    
    @property
    def description(self) -> str:
        return "Launch a new agent to handle complex, multi-step tasks autonomously"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"description", "prompt", "subagent_type"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit task delegation
        if any(phrase in request_lower for phrase in [
            "create agent", "launch agent", "delegate to agent", "sub agent", "subagent"
        ]):
            return 0.9
        
        # Medium confidence for complex multi-step requests
        if any(phrase in request_lower for phrase in [
            "complex task", "multi-step", "comprehensive", "analyze and", "search and"
        ]):
            return 0.7
        
        # Lower confidence for general task-related keywords
        if any(phrase in request_lower for phrase in [
            "task", "agent", "process", "handle", "manage"
        ]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the Task tool."""
        try:
            # Extract parameters from context
            description = context.get_state("description")
            prompt = context.get_state("prompt") 
            subagent_type = context.get_state("subagent_type")
            
            if not all([description, prompt, subagent_type]):
                return ToolResult.error_result(
                    error="Missing required parameters: description, prompt, subagent_type",
                    tool_name=self.name
                )
            
            # Validate subagent type
            available_agents = {
                "general-purpose": "General-purpose agent for researching complex questions, searching for code, and executing multi-step tasks",
                "statusline-setup": "Use this agent to configure the user's Claude Code status line setting",
                "output-style-setup": "Use this agent to create a Claude Code output style"
            }
            
            if subagent_type not in available_agents:
                return ToolResult.error_result(
                    error=f"Invalid subagent_type: {subagent_type}. Available types: {list(available_agents.keys())}",
                    tool_name=self.name
                )
            
            # For now, we'll simulate the sub-agent execution
            # In a full implementation, this would actually spawn a new agent process
            result = await self._simulate_subagent(description, prompt, subagent_type, context)
            
            return ToolResult.success_result(
                data={
                    "subagent_type": subagent_type,
                    "description": description,
                    "result": result,
                    "status": "completed"
                },
                tool_name=self.name,
                output=f"Sub-agent ({subagent_type}) completed task: {description}"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Task tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _simulate_subagent(self, description: str, prompt: str, subagent_type: str, context: ToolContext) -> str:
        """Simulate sub-agent execution."""
        # This is a simplified simulation
        # In a real implementation, this would spawn an actual sub-agent
        
        if subagent_type == "general-purpose":
            return await self._handle_general_purpose_task(prompt, context)
        elif subagent_type == "statusline-setup":
            return await self._handle_statusline_setup(prompt, context)
        elif subagent_type == "output-style-setup":
            return await self._handle_output_style_setup(prompt, context)
        else:
            return f"Simulated execution of {subagent_type} agent with prompt: {prompt}"
    
    async def _handle_general_purpose_task(self, prompt: str, context: ToolContext) -> str:
        """Handle general-purpose task delegation."""
        # Use the existing tool manager to process the request
        if context.tool_manager:
            try:
                result = await context.tool_manager.process_request(prompt, context)
                if result.success:
                    return f"General-purpose agent completed: {result.output or 'Task completed successfully'}"
                else:
                    return f"General-purpose agent encountered error: {result.error}"
            except Exception as e:
                return f"General-purpose agent execution failed: {str(e)}"
        else:
            return f"General-purpose agent would process: {prompt}"
    
    async def _handle_statusline_setup(self, prompt: str, context: ToolContext) -> str:
        """Handle statusline setup task."""
        # This would configure Claude Code statusline settings
        return f"Statusline configuration updated based on: {prompt}"
    
    async def _handle_output_style_setup(self, prompt: str, context: ToolContext) -> str:
        """Handle output style setup task.""" 
        # This would create Claude Code output styles
        return f"Output style created based on: {prompt}"


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "A short (3-5 word) description of the task"
        },
        "prompt": {
            "type": "string", 
            "description": "The task for the agent to perform"
        },
        "subagent_type": {
            "type": "string",
            "description": "The type of specialized agent to use for this task"
        }
    },
    "required": ["description", "prompt", "subagent_type"],
    "additionalProperties": False
}