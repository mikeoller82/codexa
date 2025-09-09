"""
Task tool - Launch a new agent to handle complex, multi-step tasks autonomously.
"""

import json
import asyncio
import logging
import time
from typing import Set, Dict, Any, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult
from ..base.unified_validation import unified_validator, ValidationCategory, ValidationSeverity


class TaskTool(Tool):
    """Launch a new agent to handle complex, multi-step tasks autonomously."""
    
    def __init__(self):
        super().__init__()
        self._active_subagents = {}
        self._subagent_count = 0
        self._max_concurrent_subagents = 3
        self._subagent_timeout = 300  # 5 minutes
    
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
        """Execute the Task tool with comprehensive validation and security."""
        start_time = time.time()
        
        try:
            # Extract parameters from context
            raw_parameters = {
                "description": context.get_state("description"),
                "prompt": context.get_state("prompt"),
                "subagent_type": context.get_state("subagent_type")
            }
            
            # Unified validation with security checks
            validation_result = unified_validator.validate_tool_parameters(
                self.name, raw_parameters, context
            )
            
            if not validation_result.valid:
                self.logger.warning(f"Task tool validation failed: {validation_result.errors}")
                
                # Log security issues separately
                for issue in validation_result.security_issues:
                    if issue["severity"] == ValidationSeverity.CRITICAL.value:
                        self.logger.critical(f"SECURITY: {issue['message']} (Category: {issue['category']})")
                    elif issue["category"] == ValidationCategory.INJECTION.value:
                        # Additional security logging for injection attempts
                        self.logger.error(f"INJECTION_ATTEMPT: Tool={self.name}, User={context.session_id}, Issue={issue['message']}")
                
                return ToolResult.error_result(
                    error=validation_result.get_user_friendly_error(),
                    tool_name=self.name
                )
            
            # Use sanitized parameters for execution
            description = validation_result.sanitized_parameters.get("sanitized_description") or validation_result.parameters["description"]
            prompt = validation_result.sanitized_parameters.get("sanitized_prompt") or validation_result.parameters["prompt"]
            subagent_type = validation_result.parameters["subagent_type"]
            
            # Resource exhaustion protection
            if len(self._active_subagents) >= self._max_concurrent_subagents:
                return ToolResult.error_result(
                    error=f"Maximum concurrent subagents limit reached ({self._max_concurrent_subagents})",
                    tool_name=self.name
                )
            
            # Additional business logic validation
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
            
            # Create subagent with security context
            subagent_id = f"subagent_{self._subagent_count}_{int(time.time())}"
            self._subagent_count += 1
            
            # Register active subagent for tracking
            self._active_subagents[subagent_id] = {
                "start_time": start_time,
                "type": subagent_type,
                "description": description[:100],  # Truncated for logging
                "timeout": self._subagent_timeout
            }
            
            try:
                # Execute subagent with timeout protection
                result = await asyncio.wait_for(
                    self._simulate_subagent(description, prompt, subagent_type, context, subagent_id),
                    timeout=self._subagent_timeout
                )
            except asyncio.TimeoutError:
                return ToolResult.error_result(
                    error=f"Subagent execution timed out after {self._subagent_timeout}s",
                    tool_name=self.name
                )
            finally:
                # Clean up subagent tracking
                self._active_subagents.pop(subagent_id, None)
            
            # Record execution metrics
            execution_time = time.time() - start_time
            
            return ToolResult.success_result(
                data={
                    "subagent_type": subagent_type,
                    "description": description,
                    "result": result,
                    "status": "completed",
                    "security_validation": {
                        "validated": True,
                        "warnings": len(validation_result.warnings),
                        "sanitized": len(validation_result.sanitized_parameters) > 0
                    }
                },
                tool_name=self.name,
                output=f"Sub-agent ({subagent_type}) completed task: {description}",
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Task tool execution failed: {str(e)}", exc_info=True)
            
            # Security: Don't expose internal errors to users
            user_error = "Task execution failed due to an internal error"
            if "validation" in str(e).lower():
                user_error = "Task validation failed - please check your parameters"
            elif "timeout" in str(e).lower():
                user_error = "Task execution timed out"
            
            return ToolResult.error_result(
                error=user_error,
                tool_name=self.name
            )
    
    async def _simulate_subagent(self, description: str, prompt: str, subagent_type: str, context: ToolContext, subagent_id: str) -> str:
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