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
        """Execute shell command through Serena with improved natural language support."""
        try:
            # Check if this is a natural language request
            request = context.user_request or ""
            is_natural_language = (
                len(request.split()) > 3 and
                not any(request.startswith(prefix) for prefix in ['/', '--', '-'])
            )
            
            # Extract command from request
            command = self._extract_command(context)
            
            # For natural language requests, be more helpful when no command is found
            if not command:
                if is_natural_language:
                    # Try to infer a command from the natural language request
                    inferred_command = self._infer_command_from_natural_language(request)
                    if inferred_command:
                        command = inferred_command
                        # Log that we inferred a command
                        self.logger.info(f"Inferred command from natural language: {command}")
                    else:
                        return self._create_error_result(
                            "I couldn't determine what command you want to run. Please specify the command more clearly, "
                            "for example: 'run npm install' or 'execute git status'."
                        )
                else:
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
        """Enhanced request matching for shell operations with improved natural language support."""
        confidence = super().can_handle_request(request, context)

        # Check if this is a natural language request
        is_natural_language = (
            len(request.split()) > 3 and
            not any(request.startswith(prefix) for prefix in ['/', '--', '-'])
        )

        # For natural language requests, be more lenient with command extraction
        if is_natural_language:
            # Try to extract a command - but don't immediately return 0 if we can't find one
            extracted_command = self._extract_command(context)
            if extracted_command:
                confidence = max(confidence, 0.7)  # Boost confidence if we found a command (increased from 0.6)
            else:
                # For natural language, still consider this tool even without a clear command
                # We'll try to infer one during execution
                # Give a baseline confidence for natural language that mentions command-related terms
                request_lower = request.lower()
                command_related_terms = [
                    "run", "execute", "command", "shell", "bash", "terminal", 
                    "install", "build", "start", "check", "list", "search", 
                    "create", "remove", "show", "git", "npm", "pip", "python"
                ]
                if any(term in request_lower for term in command_related_terms):
                    confidence = max(confidence, 0.4)  # Baseline confidence for command-related natural language
        else:
            # For structured requests, be more lenient than before
            extracted_command = self._extract_command(context)
            if not extracted_command:
                # Even for structured requests, don't immediately return 0
                # Try to see if we can infer a command
                inferred_command = self._infer_command_from_natural_language(request)
                if not inferred_command:
                    return 0.0
                else:
                    confidence = max(confidence, 0.5)  # We inferred a command

        request_lower = request.lower()

        # High confidence for explicit shell commands with actual commands
        shell_keywords = [
            "run", "execute", "command", "shell", "bash", "terminal",
            "install", "build", "start", "launch", "compile"
        ]

        for keyword in shell_keywords:
            if keyword in request_lower:
                # Only boost confidence if we have an actual command after the keyword
                if self._has_command_after_keyword(request, keyword):
                    confidence = max(confidence, 0.8)
                # For natural language, be more lenient
                elif is_natural_language:
                    confidence = max(confidence, 0.5)

        # Very high confidence for command-like patterns that indicate actual commands
        command_prefixes = [
            "npm ", "pip ", "git ", "python ", "node ", "make ", "./", "cd ",
            "ls ", "mkdir ", "rm ", "cp ", "mv ", "find ", "grep ", "cat ",
            "touch ", "echo ", "ps ", "df ", "free ", "yarn ", "cargo ", "go "
        ]
        if any(pattern in request for pattern in command_prefixes):
            confidence = max(confidence, 0.9)

        # Check for command structure patterns that indicate actual executable commands
        command_patterns = [
            r'run\s+[\w\-./]+',
            r'execute\s+[\w\-./]+',
            r'\$\s*[\w\-./]+',
            r'^\s*[\w\-./]+\s+[\w\-]+',
            r'command:\s*[\w\-./]+',  # Added explicit command marker
            r'shell:\s*[\w\-./]+',    # Added explicit shell marker
            r'bash:\s*[\w\-./]+'      # Added explicit bash marker
        ]

        for pattern in command_patterns:
            if re.search(pattern, request):
                confidence = max(confidence, 0.8)  # Increased from 0.7

        # For natural language requests, look for additional patterns
        if is_natural_language:
            nl_command_patterns = [
                r'using\s+[\w\-./]+',
                r'with\s+[\w\-./]+\s+command',
                r'through\s+terminal',
                r'via\s+command\s+line',
                r'in\s+shell',
                r'using\s+bash',
                r'need\s+to\s+run',
                r'want\s+to\s+execute',
                r'please\s+run',
                r'can\s+you\s+run',
                r'could\s+you\s+execute',
                r'would\s+like\s+to\s+run',
                r'should\s+execute',
                r'try\s+running',
                r'attempt\s+to\s+run'
            ]
            
            for pattern in nl_command_patterns:
                if re.search(pattern, request_lower):
                    confidence = max(confidence, 0.6)
            
            # Check for intent-based patterns that strongly suggest shell commands
            intent_patterns = {
                "install": ["install dependencies", "install packages", "install modules"],
                "build": ["build project", "build application", "compile code"],
                "run": ["run tests", "start server", "run application"],
                "check": ["check status", "view changes", "see branch"],
                "list": ["list files", "show directory", "display contents"],
                "search": ["search for files", "find text", "look for pattern"],
                "create": ["create directory", "make folder", "create file"],
                "remove": ["remove file", "delete directory", "clean up"],
                "show": ["show file contents", "display text", "view processes"]
            }
            
            for intent, phrases in intent_patterns.items():
                if any(phrase in request_lower for phrase in phrases):
                    confidence = max(confidence, 0.7)  # Strong confidence for clear intent phrases
        
        # Additional validation: ensure the extracted command looks like a real command
        # Only apply this check for non-natural language requests to avoid false negatives
        if not is_natural_language and extracted_command and not self._looks_like_command(extracted_command):
            # Don't immediately return 0, just reduce confidence
            confidence = min(confidence, 0.3)

        # For very short requests that are clearly commands, boost confidence
        if len(request.split()) <= 3 and self._looks_like_command(request):
            confidence = max(confidence, 0.9)
            
        # For requests that explicitly mention "bash" or "shell", boost confidence
        if "bash" in request_lower or "shell" in request_lower or "terminal" in request_lower:
            confidence = max(confidence, 0.7)
            
        # For requests that have quoted text that looks like a command, boost confidence
        quoted_commands = re.findall(r'["\']([^"\']+)["\']', request)
        for cmd in quoted_commands:
            if self._looks_like_command(cmd):
                confidence = max(confidence, 0.8)

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

        # Expanded list of command prefixes
        command_prefixes = [
            'npm', 'pip', 'git', 'python', 'node', 'make', './', 'cd',
            'ls', 'mkdir', 'rm', 'cp', 'mv', 'find', 'grep', 'cat',
            'touch', 'echo', 'ps', 'df', 'free', 'yarn', 'cargo', 'go',
            'mvn', './gradlew', 'ng', 'dotnet', 'docker', 'kubectl'
        ]

        # Check for command-like patterns after the keyword
        command_indicators = [
            # Check if there's any content after the keyword
            len(after_keyword) > 0,
            
            # Check for common command prefixes
            any(after_keyword.startswith(cmd) for cmd in command_prefixes),
            
            # Check for command-like patterns (command + args)
            re.search(r'[\w\-./]+\s+[\w\-./]+', after_keyword) is not None,
            
            # Check for quoted text that might be a command
            re.search(r'["\']([^"\']+)["\']', after_keyword) is not None,
            
            # Check for command markers
            re.search(r'command:\s*(.+)', after_keyword, re.IGNORECASE) is not None,
            re.search(r'shell:\s*(.+)', after_keyword, re.IGNORECASE) is not None,
            re.search(r'bash:\s*(.+)', after_keyword, re.IGNORECASE) is not None,
            
            # Check for shell syntax
            '$' in after_keyword and not after_keyword.count('$') > 3,
            
            # Check for file paths
            re.search(r'[/\\][\w\-./]+', after_keyword) is not None,
            
            # Check for options/flags
            re.search(r'-{1,2}[\w\-]+', after_keyword) is not None
        ]

        return any(command_indicators)

    def _extract_command(self, context: ToolContext) -> Optional[str]:
        """Extract shell command from request - improved for natural language support."""
        request = context.user_request or ""

        # Check if this is a natural language request
        is_natural_language = (
            len(request.split()) > 3 and
            not any(request.startswith(prefix) for prefix in ['/', '--', '-'])
        )

        # Look for commands after specific keywords with validation
        command_patterns = [
            r'(?:run|execute)\s+(.+)',  # Only run/execute, not generic "command"
            r'\$\s*(.+)',  # Shell variable/command substitution
            r'shell:\s*(.+)',
            r'bash:\s*(.+)',
            r'terminal:\s*(.+)',
            r'command:\s*(.+)'  # Added explicit command marker
        ]

        for pattern in command_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                potential_command = match.group(1).strip()
                # Be more lenient with command validation for natural language
                if is_natural_language or self._looks_like_command(potential_command):
                    return potential_command

        # Look for quoted commands with more lenient validation
        quoted_commands = re.findall(r'["\']([^"\']+)["\']', request)
        for cmd in quoted_commands:
            # For quoted text, be more lenient as it's explicitly marked by the user
            if len(cmd.split()) >= 1:  # At least one word
                return cmd

        # Check if entire request looks like a command (very restrictive)
        if self._looks_like_command(request) and self._is_clear_command_request(request):
            return request.strip()

        # Look for common command prefixes only if they appear to be actual commands
        command_prefixes = [
            "npm", "pip", "python", "node", "git", "make", "docker",
            "curl", "wget", "ls", "cd", "mkdir", "cp", "mv", "rm",
            "chmod", "chown", "ps", "kill", "which", "echo", "cat",
            "find", "grep", "touch", "nano", "vim", "code", "ssh"  # Added more common commands
        ]

        words = request.split()
        if (words and
            words[0].lower() in command_prefixes):
            # Be more lenient with command validation
            return request.strip()

        # For natural language requests, try to extract commands more aggressively
        if is_natural_language:
            # Look for command-like patterns in natural language
            nl_command_patterns = [
                # Look for "run X" or "execute X" anywhere in the request
                r'(?:run|execute|use)\s+([\w\-./]+(?:\s+[\w\-./]+){0,5})',  # Increased argument count
                # Look for command with arguments
                r'(?:with|using)\s+([\w\-./]+(?:\s+[\w\-./]+){0,5})',  # Increased argument count
                # Look for "X command" patterns
                r'([\w\-./]+(?:\s+[\w\-./]+){0,5})\s+command',  # Increased argument count
                # Look for "I want to X" patterns
                r'(?:I want to|I need to|please|can you)\s+(?:run|execute|use)?\s*([\w\-./]+(?:\s+[\w\-./]+){0,5})',
                # Look for "do X" patterns
                r'(?:do|perform|try)\s+([\w\-./]+(?:\s+[\w\-./]+){0,5})'
            ]
            
            for pattern in nl_command_patterns:
                matches = re.findall(pattern, request, re.IGNORECASE)
                for match in matches:
                    potential_command = match.strip()
                    # Be more lenient with command validation for natural language
                    if len(potential_command.split()) >= 1:  # At least one word
                        return potential_command
            
            # Extract potential commands from the request
            words = request.split()
            for i in range(len(words)):
                if words[i].lower() in command_prefixes and i+1 < len(words):
                    # Extract command and up to 5 arguments (increased from 3)
                    end_idx = min(i+6, len(words))
                    potential_command = ' '.join(words[i:end_idx])
                    return potential_command

            # Last resort: try to infer a command from the natural language request
            inferred_command = self._infer_command_from_natural_language(request)
            if inferred_command:
                return inferred_command

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
        
        # Empty text is not a command
        if not text:
            return False
            
        # Expanded list of command prefixes
        command_prefixes = [
            'npm', 'pip', 'python', 'node', 'git', 'make', 'docker',
            'curl', 'wget', 'ls', 'cd', 'mkdir', 'cp', 'mv', 'rm',
            'find', 'grep', 'cat', 'touch', 'echo', 'ps', 'df', 'free',
            'yarn', 'cargo', 'go', 'mvn', './gradlew', 'ng', 'dotnet',
            'kubectl', 'terraform', 'ansible', 'ssh', 'scp', 'rsync',
            'tar', 'zip', 'unzip', 'chmod', 'chown', 'sudo', 'apt',
            'yum', 'brew', 'code', 'vim', 'nano', 'less', 'more'
        ]
        
        # Check for common command patterns
        command_indicators = [
            # Path-like patterns
            text.startswith('./'),
            text.startswith('~/'),
            text.startswith('/'),
            
            # Option flags
            ' --' in text,
            ' -' in text and len(text.split()) > 1,
            
            # Common command prefixes
            any(text.startswith(cmd) for cmd in command_prefixes),
            
            # Command with arguments pattern
            re.match(r'^\w+\s+[\w\-./]+', text) is not None,
            
            # Shell syntax
            '$' in text and not text.count('$') > 3,
            
            # Pipe or redirection
            '|' in text or '>' in text or '<' in text,
            
            # Environment variables
            re.search(r'\$\w+', text) is not None,
            
            # File paths in arguments
            re.search(r'\s+[/\\][\w\-./]+', text) is not None,
            
            # Options/flags anywhere
            re.search(r'\s-{1,2}[\w\-]+', text) is not None,
            
            # Command with quoted arguments
            re.search(r'\w+\s+["\']([^"\']+)["\']', text) is not None,
            
            # Command with file extension arguments
            re.search(r'\w+\s+[\w\-./]+\.[a-zA-Z0-9]+', text) is not None
        ]
        
        # For very short commands (1-2 words), be more lenient
        if len(text.split()) <= 2:
            # Check if it's a single word that matches a common command
            if text.split()[0] in command_prefixes:
                return True
                
            # Check if it's a simple command with one argument
            if len(text.split()) == 2 and text.split()[0] in command_prefixes:
                return True
        
        return any(command_indicators)

    def _infer_command_from_natural_language(self, request: str) -> Optional[str]:
        """Attempt to infer a shell command from a natural language request."""
        request_lower = request.lower()
        
        # Common command mappings for natural language
        command_mappings = {
            "install": {
                "npm": "npm install",
                "package": "npm install",
                "dependency": "npm install",
                "dependencies": "npm install",
                "node": "npm install",
                "javascript": "npm install",
                "js": "npm install",
                "python": "pip install",
                "pip": "pip install",
                "requirements": "pip install -r requirements.txt",
                "gems": "gem install",
                "ruby": "gem install",
                "go": "go get",
                "rust": "cargo install",
                "cargo": "cargo install",
            },
            "build": {
                "project": "npm run build",
                "app": "npm run build",
                "application": "npm run build",
                "frontend": "npm run build",
                "react": "npm run build",
                "vue": "npm run build",
                "angular": "ng build",
                "webpack": "webpack",
                "gradle": "./gradlew build",
                "maven": "mvn package",
                "java": "mvn package",
                "rust": "cargo build",
                "go": "go build",
            },
            "run": {
                "tests": "npm test",
                "test": "npm test",
                "server": "npm start",
                "app": "npm start",
                "application": "npm start",
                "dev": "npm run dev",
                "development": "npm run dev",
                "python": "python",
                "script": "python",
                "node": "node",
                "javascript": "node",
            },
            "check": {
                "status": "git status",
                "changes": "git status",
                "git": "git status",
                "branch": "git branch",
                "commits": "git log",
                "history": "git log",
                "diff": "git diff",
                "version": "git --version",
            },
            "list": {
                "files": "ls -la",
                "directory": "ls -la",
                "folder": "ls -la",
                "contents": "ls -la",
                "current": "pwd",
                "location": "pwd",
            },
            "search": {
                "files": "find . -type f -name",
                "text": "grep -r",
                "pattern": "grep -r",
                "content": "grep -r",
            },
            "create": {
                "directory": "mkdir",
                "folder": "mkdir",
                "file": "touch",
            },
            "remove": {
                "file": "rm",
                "directory": "rm -r",
                "folder": "rm -r",
            },
            "show": {
                "file": "cat",
                "content": "cat",
                "text": "cat",
                "processes": "ps aux",
                "memory": "free -h",
                "disk": "df -h",
            }
        }
        
        # Try to match intent and subject
        for intent, subjects in command_mappings.items():
            if intent in request_lower:
                for subject, command in subjects.items():
                    if subject in request_lower:
                        # Check if there's a specific file or argument mentioned
                        file_match = re.search(r'(?:file|named|called)\s+["\']?([^"\'<>\n]+\.[a-zA-Z0-9]+)["\']?', request_lower)
                        if file_match and (intent in ["run", "show", "search", "create", "remove"]):
                            return f"{command} {file_match.group(1)}"
                        return command
        
        # Try to extract specific commands mentioned in the request
        command_prefixes = [
            "npm", "pip", "python", "node", "git", "make", "docker",
            "curl", "wget", "ls", "cd", "mkdir", "cp", "mv", "rm",
            "find", "grep", "touch", "cat", "echo", "ps", "df", "free",
            "yarn", "cargo", "go", "mvn", "./gradlew", "ng", "dotnet"
        ]
        
        words = request_lower.split()
        for i, word in enumerate(words):
            if word in command_prefixes and i < len(words) - 1:
                # Extract the command and up to 5 arguments (increased from 3)
                end_idx = min(i + 6, len(words))
                return ' '.join(words[i:end_idx])
        
        # Look for specific action phrases - expanded list
        action_phrases = {
            # Git operations
            "check git status": "git status",
            "see git status": "git status",
            "view git changes": "git status",
            "check branch": "git branch",
            "view commit history": "git log",
            "check git diff": "git diff",
            "view git version": "git --version",
            
            # Package management
            "install dependencies": "npm install",
            "install packages": "npm install",
            "install node modules": "npm install",
            "install node packages": "npm install",
            "install python packages": "pip install",
            "install python requirements": "pip install -r requirements.txt",
            "install python dependencies": "pip install -r requirements.txt",
            "install requirements": "pip install -r requirements.txt",
            
            # Build and run
            "run tests": "npm test",
            "run the tests": "npm test",
            "execute tests": "npm test",
            "start server": "npm start",
            "run server": "npm start",
            "start the server": "npm start",
            "run the server": "npm start",
            "build project": "npm run build",
            "build the project": "npm run build",
            "compile project": "npm run build",
            "build application": "npm run build",
            
            # File operations
            "list files": "ls -la",
            "show files": "ls -la",
            "list all files": "ls -la",
            "show all files": "ls -la",
            "show directory": "ls -la",
            "list directory": "ls -la",
            "show current directory": "pwd",
            "check current directory": "pwd",
            "where am i": "pwd",
            "current location": "pwd",
            
            # System information
            "show processes": "ps aux",
            "list processes": "ps aux",
            "check memory": "free -h",
            "show memory usage": "free -h",
            "check disk space": "df -h",
            "show disk usage": "df -h"
        }
        
        # Check for exact phrases first
        for phrase, command in action_phrases.items():
            if phrase in request_lower:
                return command
        
        # Check for partial matches with key terms
        key_terms = {
            "git status": ["git status", "changes", "modified"],
            "ls -la": ["list files", "show files", "directory contents"],
            "npm install": ["install dependencies", "node modules", "package.json"],
            "pip install -r requirements.txt": ["python dependencies", "requirements file"],
            "npm test": ["run tests", "execute tests", "test suite"],
            "npm start": ["start server", "run application", "launch app"],
            "npm run build": ["build project", "compile", "bundle"],
            "pwd": ["current directory", "where am i", "location"],
            "ps aux": ["running processes", "process list"],
            "free -h": ["memory usage", "ram usage"],
            "df -h": ["disk space", "storage usage"]
        }
        
        for command, terms in key_terms.items():
            if any(term in request_lower for term in terms):
                return command
        
        # Last resort: check for common verbs followed by nouns
        verb_noun_patterns = [
            (r'(?:run|execute|start)\s+(\w+)', "run"),
            (r'(?:build|compile)\s+(\w+)', "build"),
            (r'(?:install|add)\s+(\w+)', "install"),
            (r'(?:list|show|display)\s+(\w+)', "list"),
            (r'(?:create|make)\s+(\w+)', "create"),
            (r'(?:remove|delete)\s+(\w+)', "remove"),
            (r'(?:check|view)\s+(\w+)', "check")
        ]
        
        for pattern, intent in verb_noun_patterns:
            matches = re.findall(pattern, request_lower)
            if matches:
                noun = matches[0]
                # Check if we have a mapping for this verb-noun combination
                if intent in command_mappings and noun in command_mappings[intent]:
                    return command_mappings[intent][noun]
        
        return None

    def _is_clear_command_request(self, request: str) -> bool:
        """Check if the request clearly indicates a shell command should be executed."""
        request_lower = request.lower()

        # Expanded list of command prefixes
        command_prefixes = [
            'npm ', 'pip ', 'git ', 'python ', 'node ', 'make ', 'docker ',
            './', 'cd ', 'ls ', 'mkdir ', 'cp ', 'mv ', 'rm ', 'find ', 'grep ',
            'cat ', 'touch ', 'echo ', 'ps ', 'df ', 'free ', 'yarn ', 'cargo ',
            'go ', 'mvn ', './gradlew ', 'ng ', 'dotnet ', 'kubectl ', 'terraform ',
            'ansible ', 'ssh ', 'scp ', 'rsync ', 'tar ', 'zip ', 'unzip ',
            'chmod ', 'chown ', 'sudo ', 'apt ', 'yum ', 'brew ', 'code ', 'vim ',
            'nano '
        ]

        # Must have clear command intent
        command_indicators = [
            # Explicit command prefixes
            any(request.startswith(prefix) for prefix in command_prefixes),
            
            # Command-like structure
            bool(re.search(r'^\w+\s+[\w\-./]', request)),  # word + space + word/path
            
            # Shell syntax
            '$' in request and not request.count('$') > 3,  # Has $ but not too many (avoid template strings)
            
            # Pipe or redirection
            '|' in request or '>' in request or '<' in request,
            
            # Environment variables
            re.search(r'\$\w+', request) is not None,
            
            # Options/flags
            re.search(r'\s-{1,2}[\w\-]+', request) is not None,
            
            # Command with quoted arguments
            re.search(r'^\w+\s+["\']([^"\']+)["\']', request) is not None,
            
            # Command with file extension arguments
            re.search(r'^\w+\s+[\w\-./]+\.[a-zA-Z0-9]+', request) is not None,
            
            # Explicit command markers
            re.search(r'^command:\s*(.+)', request, re.IGNORECASE) is not None,
            re.search(r'^shell:\s*(.+)', request, re.IGNORECASE) is not None,
            re.search(r'^bash:\s*(.+)', request, re.IGNORECASE) is not None
        ]

        # Expanded list of conversational indicators
        conversational_indicators = [
            "how do i", "what is", "explain", "tell me about", "show me",
            "can you", "would you", "could you", "help me", "why does", 
            "when should", "how can i", "how does", "what are", "what should",
            "how to", "is there", "are there", "do you know", "i'm trying to",
            "i am trying to", "i don't know", "i do not know"
        ]
        
        # Some phrases that look conversational but are actually command requests
        command_request_phrases = [
            "please run", "can you run", "could you execute", "please execute",
            "i want to run", "i need to run", "let me run", "i want to execute",
            "i need to execute", "can you execute", "would you run"
        ]

        has_command_intent = any(command_indicators)
        has_conversational_intent = any(indicator in request_lower for indicator in conversational_indicators)
        has_command_request_phrase = any(phrase in request_lower for phrase in command_request_phrases)

        # If it's a very short request (1-3 words), be more lenient
        if len(request.split()) <= 3:
            # If it starts with a command prefix, it's likely a command
            if any(request.startswith(prefix) for prefix in command_prefixes):
                return True
                
            # If it's a single word that's a common command, it's likely a command
            if len(request.split()) == 1 and request.strip() in [prefix.strip() for prefix in command_prefixes]:
                return True

        # Return true if we have clear command intent and either:
        # 1. No conversational intent, or
        # 2. Has a command request phrase that overrides conversational intent
        return has_command_intent and (not has_conversational_intent or has_command_request_phrase)

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