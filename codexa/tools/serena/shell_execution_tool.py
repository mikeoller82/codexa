"""
Serena-based shell execution tool.
"""

from typing import Dict, Any, Set, List, Optional
import re
import shlex

from ..base.tool_interface import ToolResult, ToolContext
from .base_serena_tool import BaseSerenaTool


class ShellExecutionTool(BaseSerenaTool):
    """Tool for executing shell commands through Serena with project context."""
    
    @property
    def name(self) -> str:
        return "serena_shell_execution"
    
    @property
    def description(self) -> str:
        return "Execute shell commands with project context and enhanced error handling"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "shell-execution", "command-execution", "project-commands",
            "build-commands", "test-commands", "dev-commands"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["execute_shell_command"]
    
    @property
    def timeout_seconds(self) -> float:
        """Extended timeout for shell operations."""
        return 120.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute shell command through Serena."""
        try:
            # Extract command from request
            command = self._extract_command(context)
            if not command:
                return self._create_error_result("No shell command provided")
            
            # Extract working directory
            working_dir = self._extract_working_directory(context)
            
            # Extract timeout if specified
            timeout = self._extract_timeout(context)
            
            # Validate command safety (basic checks)
            if not self._is_command_safe(command):
                return self._create_error_result(f"Command not allowed for security reasons: {command}")
            
            # Build execution parameters
            exec_params = {"command": command}
            if working_dir:
                exec_params["working_directory"] = working_dir
            
            # Execute command through Serena
            result = await self.call_serena_tool(
                "execute_shell_command", 
                exec_params, 
                timeout=timeout
            )
            
            if result is None:
                return self._create_error_result("Command execution failed - no result returned")
            
            # Parse execution result
            success = result.get("success", False)
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", -1)
            
            # Format output
            output_parts = [f"Command: {command}"]
            if working_dir:
                output_parts.append(f"Working Directory: {working_dir}")
            output_parts.append(f"Exit Code: {exit_code}")
            
            if stdout:
                output_parts.append(f"\nStdout:\n{stdout}")
            if stderr:
                output_parts.append(f"\nStderr:\n{stderr}")
            
            output = "\n".join(output_parts)
            
            # Determine if this was successful
            command_success = success and exit_code == 0
            
            return self._create_success_result(
                data={
                    "command": command,
                    "working_directory": working_dir,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "success": command_success,
                    "timeout": timeout
                },
                output=output
            ) if command_success else self._create_error_result(
                f"Command failed with exit code {exit_code}: {command}\n{stderr}",
                data={
                    "command": command,
                    "working_directory": working_dir,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr
                }
            )
            
        except Exception as e:
            return self._create_error_result(f"Shell execution failed: {e}")
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Enhanced request matching for shell operations - only match when actual commands are present."""
        confidence = super().can_handle_request(request, context)

        # First check if we can actually extract a command - if not, return 0
        extracted_command = self._extract_command(context)
        if not extracted_command:
            return 0.0

        request_lower = request.lower()

        # High confidence for explicit shell commands with actual commands
        shell_keywords = [
            "run", "execute", "command", "shell", "bash", "terminal"
        ]

        for keyword in shell_keywords:
            if keyword in request_lower:
                # Only boost confidence if we have an actual command after the keyword
                if self._has_command_after_keyword(request, keyword):
                    confidence = max(confidence, 0.8)

        # Very high confidence for command-like patterns that indicate actual commands
        command_prefixes = ["npm ", "pip ", "git ", "python ", "node ", "make ", "./", "cd "]
        if any(pattern in request for pattern in command_prefixes):
            confidence = max(confidence, 0.9)

        # Check for command structure patterns that indicate actual executable commands
        command_patterns = [
            r'run\s+[\w\-./]+',
            r'execute\s+[\w\-./]+',
            r'\$\s*[\w\-./]+',
            r'^\s*[\w\-./]+\s+[\w\-]+'
        ]

        for pattern in command_patterns:
            if re.search(pattern, request):
                confidence = max(confidence, 0.7)

        # Additional validation: ensure the extracted command looks like a real command
        if extracted_command and not self._looks_like_command(extracted_command):
            return 0.0

        return confidence

    def _has_command_after_keyword(self, request: str, keyword: str) -> bool:
        """Check if there's an actual command after a keyword."""
        keyword_pos = request.lower().find(keyword.lower())
        if keyword_pos == -1:
            return False

        # Get text after the keyword
        after_keyword = request[keyword_pos + len(keyword):].strip()

        # Check if there's meaningful content after the keyword
        if not after_keyword:
            return False

        # Check for command-like patterns after the keyword
        command_indicators = [
            after_keyword.startswith((' ', '\t')),
            any(after_keyword.startswith(cmd) for cmd in ['npm', 'pip', 'git', 'python', 'node', 'make', './', 'cd']),
            re.search(r'[\w\-./]+\s+[\w\-]+', after_keyword) is not None
        ]

        return any(command_indicators)

    def _extract_command(self, context: ToolContext) -> Optional[str]:
        """Extract shell command from request - be more restrictive to avoid false positives."""
        request = context.user_request or ""

        # Look for commands after specific keywords with validation
        command_patterns = [
            r'(?:run|execute)\s+(.+)',  # Only run/execute, not generic "command"
            r'\$\s*(.+)',  # Shell variable/command substitution
            r'shell:\s*(.+)',
            r'bash:\s*(.+)'
        ]

        for pattern in command_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                potential_command = match.group(1).strip()
                if self._looks_like_command(potential_command):
                    return potential_command

        # Look for quoted commands with validation
        quoted_commands = re.findall(r'["\']([^"\']+)["\']', request)
        for cmd in quoted_commands:
            if self._looks_like_command(cmd):
                return cmd

        # Check if entire request looks like a command (very restrictive)
        if self._looks_like_command(request) and self._is_clear_command_request(request):
            return request.strip()

        # Look for common command prefixes only if they appear to be actual commands
        command_prefixes = [
            "npm", "pip", "python", "node", "git", "make", "docker",
            "curl", "wget", "ls", "cd", "mkdir", "cp", "mv", "rm",
            "chmod", "chown", "ps", "kill", "which", "echo", "cat"
        ]

        words = request.split()
        if (words and
            words[0].lower() in command_prefixes and
            self._is_clear_command_request(request)):
            return request.strip()

        return None
    
    def _extract_working_directory(self, context: ToolContext) -> Optional[str]:
        """Extract working directory from request or context."""
        request = context.user_request or ""
        
        # Look for explicit directory specification
        dir_patterns = [
            r'in\s+directory\s+(.+?)(?:\s|$)',
            r'in\s+(.+?)(?:\s|$)',
            r'from\s+(.+?)(?:\s|$)',
            r'cd\s+(.+?)(?:\s|$)'
        ]
        
        for pattern in dir_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                potential_dir = match.group(1).strip()
                # Basic validation
                if not potential_dir.startswith('-') and ('/' in potential_dir or potential_dir.startswith('.')):
                    return potential_dir
        
        # Use current path from context safely
        return self._get_current_path(context)
    
    def _extract_timeout(self, context: ToolContext) -> Optional[float]:
        """Extract timeout from request."""
        request = context.user_request or ""
        
        # Look for timeout specification
        timeout_patterns = [
            r'timeout\s+(\d+)',
            r'wait\s+(\d+)',
            r'(\d+)\s*seconds?'
        ]
        
        for pattern in timeout_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    def _looks_like_command(self, text: str) -> bool:
        """Check if text looks like a shell command."""
        text = text.strip()
        
        # Check for common command patterns
        command_indicators = [
            text.startswith('./'),
            text.startswith('~/'),
            text.startswith('/'),
            ' --' in text,
            ' -' in text and len(text.split()) > 1,
            any(text.startswith(cmd) for cmd in [
                'npm', 'pip', 'python', 'node', 'git', 'make', 'docker',
                'curl', 'wget', 'ls', 'cd', 'mkdir', 'cp', 'mv', 'rm'
            ])
        ]
        
        return any(command_indicators)

    def _is_clear_command_request(self, request: str) -> bool:
        """Check if the request clearly indicates a shell command should be executed."""
        request_lower = request.lower()

        # Must have clear command intent
        command_indicators = [
            # Explicit command prefixes
            request.startswith(('npm ', 'pip ', 'git ', 'python ', 'node ', 'make ', 'docker ')),
            request.startswith(('./', 'cd ', 'ls ', 'mkdir ', 'cp ', 'mv ', 'rm ')),
            # Command-like structure
            bool(re.search(r'^\w+\s+[\w\-./]', request)),  # word + space + word/path
            # Shell syntax
            '$' in request and not request.count('$') > 3,  # Has $ but not too many (avoid template strings)
        ]

        # Must NOT have conversational indicators that suggest this isn't a command
        conversational_indicators = [
            "how do i", "what is", "explain", "tell me about", "show me",
            "can you", "please", "would you", "could you", "help me",
            "i want to", "i need to", "let me", "why does", "when should"
        ]

        has_command_intent = any(command_indicators)
        has_conversational_intent = any(indicator in request_lower for indicator in conversational_indicators)

        # Only return true if we have clear command intent and no conversational intent
        return has_command_intent and not has_conversational_intent

    def _is_command_safe(self, command: str) -> bool:
        """Basic command safety validation."""
        command_lower = command.lower()
        
        # Block potentially dangerous commands
        dangerous_patterns = [
            'rm -rf /',
            'dd if=',
            ':(){ :|:& };:',  # fork bomb
            'chmod 777',
            'chown root',
            'sudo su',
            'mkfs.',
            'fdisk',
            'format',
            '> /dev/',
            'shred',
            'wipefs'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return False
        
        # Block commands that modify system files
        system_paths = ['/etc/', '/usr/', '/var/', '/sys/', '/proc/', '/dev/']
        for path in system_paths:
            if f'rm {path}' in command_lower or f'rm -rf {path}' in command_lower:
                return False
        
        # Allow most other commands
        return True
    
    def get_common_commands_help(self) -> str:
        """Get help text for common development commands."""
        return """
Common development commands you can run:

Build & Package Management:
  npm install          - Install Node.js dependencies
  npm run build        - Build the project
  pip install -r requirements.txt - Install Python dependencies
  python setup.py build - Build Python project

Testing:
  npm test             - Run Node.js tests
  python -m pytest    - Run Python tests
  make test            - Run make-based tests

Git Operations:
  git status           - Check git status
  git add .            - Stage all changes
  git commit -m "msg"  - Commit changes
  git push             - Push to remote

Development:
  python app.py        - Run Python application
  npm start            - Start Node.js application
  make                 - Build using Makefile

File Operations:
  ls -la               - List directory contents
  pwd                  - Show current directory
  cat filename         - Display file contents

Note: Commands are executed with project context when available.
        """