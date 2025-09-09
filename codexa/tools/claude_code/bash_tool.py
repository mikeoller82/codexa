"""
Bash tool - Executes bash commands in a persistent shell session.
"""

import asyncio
import subprocess
import os
import uuid
from typing import Set, Dict, Any, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class BashTool(Tool):
    """Executes bash commands in a persistent shell session."""
    
    # Claude Code schema compatibility  
    CLAUDE_CODE_SCHEMA = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute"
            },
            "timeout": {
                "type": "number",
                "description": "Optional timeout in milliseconds (max 600000)"
            },
            "description": {
                "type": "string",
                "description": "Clear, concise description of what this command does in 5-10 words"
            },
            "run_in_background": {
                "type": "boolean",
                "description": "Set to true to run this command in the background"
            }
        },
        "required": ["command"],
        "additionalProperties": False
    }
    
    def __init__(self):
        super().__init__()
        self._shells: Dict[str, subprocess.Popen] = {}
        self._shell_outputs: Dict[str, list] = {}
    
    @property
    def name(self) -> str:
        return "Bash"
    
    @property
    def description(self) -> str:
        return "Executes a given bash command in a persistent shell session with optional timeout"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return set()  # Command can be derived from user request
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit command execution
        if any(phrase in request_lower for phrase in [
            "run command", "execute command", "bash", "shell", "command line"
        ]):
            return 0.9
        
        # Medium confidence for common command patterns
        if any(phrase in request_lower for phrase in [
            "ls ", "cd ", "mkdir", "cp ", "mv ", "rm ", "grep ", "find ",
            "git ", "npm ", "pip ", "python ", "node ", "make", "echo "
        ]):
            return 0.7
        
        # Lower confidence for general execution keywords
        if any(phrase in request_lower for phrase in [
            "execute", "run", "command", "terminal"
        ]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the Bash tool."""
        try:
            # Extract parameters
            command = context.get_state("command") or context.user_request or ""
            timeout = context.get_state("timeout", 120000)  # Default 2 minutes in ms
            description = context.get_state("description", "Execute bash command")
            run_in_background = context.get_state("run_in_background", False)
            
            if not command:
                return ToolResult.error_result(
                    error="Missing required parameter: command",
                    tool_name=self.name
                )
            
            # Validate command - reject obviously invalid commands
            command = command.strip()
            
            # Check for single words that are not valid shell commands
            invalid_single_words = {
                "turn", "return", "and", "or", "but", "if", "then", "else", 
                "when", "where", "what", "how", "why", "this", "that", "these", "those"
            }
            
            if len(command.split()) == 1 and command.lower() in invalid_single_words:
                return ToolResult.error_result(
                    error=f"Invalid command: '{command}' is not a valid shell command. "
                          "Please provide a proper shell command (e.g., 'ls', 'pwd', 'echo hello').",
                    tool_name=self.name
                )
            
            # Convert timeout from milliseconds to seconds
            timeout_seconds = timeout / 1000.0 if timeout else None
            
            # Validate timeout limits
            if timeout_seconds and timeout_seconds > 600:  # Max 10 minutes
                timeout_seconds = 600
            
            # Execute command
            if run_in_background:
                return await self._execute_background(command, context)
            else:
                return await self._execute_foreground(command, timeout_seconds, context)
                
        except Exception as e:
            return ToolResult.error_result(
                error=f"Bash tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _execute_foreground(self, command: str, timeout_seconds: Optional[float], context: ToolContext) -> ToolResult:
        """Execute command in foreground with timeout."""
        try:
            # Set working directory
            cwd = context.current_dir or context.current_path or os.getcwd()
            
            # Create process
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult.error_result(
                    error=f"Command timed out after {timeout_seconds} seconds",
                    tool_name=self.name
                )
            
            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            # Combine output
            combined_output = ""
            if stdout_text:
                combined_output += stdout_text
            if stderr_text:
                if combined_output:
                    combined_output += "\n"
                combined_output += stderr_text
            
            # Determine success based on return code
            success = process.returncode == 0
            
            # Truncate output if too long (30000 character limit)
            if len(combined_output) > 30000:
                combined_output = combined_output[:30000] + "\n[Output truncated...]"
            
            if success:
                return ToolResult.success_result(
                    data={
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "return_code": process.returncode,
                        "command": command
                    },
                    tool_name=self.name,
                    output=combined_output or "Command completed successfully"
                )
            else:
                return ToolResult.error_result(
                    error=f"Command failed with exit code {process.returncode}: {stderr_text}",
                    tool_name=self.name
                )
                
        except Exception as e:
            return ToolResult.error_result(
                error=f"Command execution failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _execute_background(self, command: str, context: ToolContext) -> ToolResult:
        """Execute command in background."""
        try:
            # Generate shell ID
            shell_id = str(uuid.uuid4())
            
            # Set working directory
            cwd = context.current_dir or context.current_path or os.getcwd()
            
            # Create background process
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Store shell reference
            self._shells[shell_id] = process
            self._shell_outputs[shell_id] = []
            
            # Start output collection task
            asyncio.create_task(self._collect_background_output(shell_id, process))
            
            return ToolResult.success_result(
                data={
                    "shell_id": shell_id,
                    "command": command,
                    "status": "running"
                },
                tool_name=self.name,
                output=f"Command started in background with shell ID: {shell_id}"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Background command execution failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _collect_background_output(self, shell_id: str, process: subprocess.Popen):
        """Collect output from background process."""
        try:
            stdout, stderr = await process.communicate()
            
            # Store output
            output_data = {
                "stdout": stdout.decode('utf-8', errors='replace') if stdout else "",
                "stderr": stderr.decode('utf-8', errors='replace') if stderr else "",
                "return_code": process.returncode,
                "completed": True
            }
            
            self._shell_outputs[shell_id].append(output_data)
            
        except Exception as e:
            # Store error
            self._shell_outputs[shell_id].append({
                "error": str(e),
                "completed": True
            })
    
    def get_background_output(self, shell_id: str, filter_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Get output from background shell."""
        if shell_id not in self._shell_outputs:
            return {"error": f"Shell ID not found: {shell_id}"}
        
        output = self._shell_outputs[shell_id]
        if not output:
            return {"status": "running", "output": ""}
        
        latest = output[-1]
        
        # Apply filter if specified
        if filter_pattern and "stdout" in latest:
            import re
            lines = latest["stdout"].split('\n')
            filtered_lines = [line for line in lines if re.search(filter_pattern, line)]
            latest["stdout"] = '\n'.join(filtered_lines)
        
        return latest
    
    def kill_background_shell(self, shell_id: str) -> Dict[str, Any]:
        """Kill background shell."""
        if shell_id not in self._shells:
            return {"error": f"Shell ID not found: {shell_id}"}
        
        try:
            process = self._shells[shell_id]
            process.kill()
            
            # Cleanup
            del self._shells[shell_id]
            if shell_id in self._shell_outputs:
                del self._shell_outputs[shell_id]
            
            return {"success": True, "message": f"Shell {shell_id} terminated"}
            
        except Exception as e:
            return {"error": f"Failed to kill shell: {str(e)}"}


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The command to execute"
        },
        "timeout": {
            "type": "number",
            "description": "Optional timeout in milliseconds (max 600000)"
        },
        "description": {
            "type": "string",
            "description": "Clear, concise description of what this command does in 5-10 words"
        },
        "run_in_background": {
            "type": "boolean",
            "description": "Set to true to run this command in the background"
        }
    },
    "required": ["command"],
    "additionalProperties": False
}