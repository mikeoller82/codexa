"""
Basic Bash Tool for Codexa.
Provides shell command execution functionality.
"""

import subprocess
import asyncio
from typing import Set, Dict, Any
import tempfile
import os

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority


class BashTool(Tool):
    """Tool for executing bash commands."""

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute bash commands and shell operations"

    @property
    def category(self) -> str:
        return "system"

    @property
    def capabilities(self) -> Set[str]:
        return {"command_execution", "shell", "system_operations"}

    @property
    def priority(self) -> ToolPriority:
        """Higher priority for basic bash tool to ensure it's used over Claude Code version."""
        return ToolPriority.HIGH

    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()

        # High confidence for explicit bash/shell commands
        if any(keyword in request_lower for keyword in [
            "bash", "shell", "command", "execute", "run", "cmd"
        ]):
            return 0.9

        # Medium confidence for system operations
        if any(keyword in request_lower for keyword in [
            "list", "ls", "dir", "cat", "find", "grep", "ps", "kill"
        ]):
            return 0.6

        return 0.0

    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute bash command."""
        try:
            # First try to get command from context state (set by tool manager)
            command = context.get_state("command")

            # If not in context state, extract from request
            if not command:
                command = self._extract_command(context.user_request)

            if not command:
                return ToolResult.error_result(
                    error="No command found in request",
                    tool_name=self.name
                )

            # Execute command
            result = await self._execute_command(command)

            return ToolResult.success_result(
                data={
                    "command": command,
                    "exit_code": result["exit_code"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"]
                },
                tool_name=self.name,
                output=f"Command executed: {command}"
            )

        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to execute command: {str(e)}",
                tool_name=self.name
            )

    def _extract_command(self, request: str) -> str:
        """Extract command from request string."""
        # Simple extraction - look for command-like patterns
        import re

        # Remove common prefixes
        request = request.lower()
        for prefix in ["run ", "execute ", "bash ", "shell ", "command "]:
            if request.startswith(prefix):
                request = request[len(prefix):]

        # Extract quoted commands or first word
        match = re.search(r'["\']([^"\']+)["\']|(\w+)', request)
        if match:
            return match.group(1) or match.group(2)

        return request.strip()

    async def _execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a bash command and return results."""
        try:
            # Run command in subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )

            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )

            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()

            return {
                "exit_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "command": command
            }

        except asyncio.TimeoutError:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "command": command
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "command": command
            }