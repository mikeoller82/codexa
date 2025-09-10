"""
Claude Code tool registry integration.

This module provides functionality to register Claude Code tools with the Codexa tool system
and handle schema validation and parameter extraction from user requests.
"""

import json
import re
from typing import Dict, Any, List, Optional, Type
from ..base.tool_interface import Tool, ToolContext


class ClaudeCodeRegistry:
    """Registry for Claude Code tools with schema validation and parameter extraction."""
    
    def __init__(self):
        self.tools: Dict[str, Type[Tool]] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
    
    def register_claude_code_tools(self, tool_registry):
        """Register all Claude Code tools with the Codexa tool registry."""
        from . import (
            TaskTool, BashTool, GlobTool, GrepTool, LSTool,
            ReadTool, EditTool, MultiEditTool, WriteTool,
            WebFetchTool, WebSearchTool, TodoWriteTool,
            NotebookEditTool, BashOutputTool, KillBashTool
        )
        
        # Core tools (always available)
        core_tools = [
            TaskTool, BashTool, GlobTool, GrepTool, LSTool,
            ReadTool, EditTool, MultiEditTool, WriteTool,
            TodoWriteTool, NotebookEditTool, BashOutputTool, KillBashTool
        ]
        
        # Web tools (optional, may be None)
        web_tools = [WebFetchTool, WebSearchTool]
        
        # Register core tools
        for tool_class in core_tools:
            if tool_class is not None:
                # Register with Codexa registry
                tool_registry.register_tool(tool_class)
                
                # Store in our registry for schema handling
                tool_name = tool_class().name
                self.tools[tool_name] = tool_class
                
                # Extract schema if available
                if hasattr(tool_class, 'CLAUDE_CODE_SCHEMA'):
                    self.schemas[tool_name] = tool_class.CLAUDE_CODE_SCHEMA
        
        # Register web tools if available
        for tool_class in web_tools:
            if tool_class is not None:
                try:
                    # Register with Codexa registry
                    tool_registry.register_tool(tool_class)
                    
                    # Store in our registry for schema handling
                    tool_name = tool_class().name
                    self.tools[tool_name] = tool_class
                    
                    # Extract schema if available
                    if hasattr(tool_class, 'CLAUDE_CODE_SCHEMA'):
                        self.schemas[tool_name] = tool_class.CLAUDE_CODE_SCHEMA
                except Exception as e:
                    print(f"Could not register web tool {tool_class}: {e}")
    
    def extract_parameters_from_request(self, tool_name: str, request: str, 
                                      context: ToolContext) -> Dict[str, Any]:
        """Extract parameters from a natural language request for a Claude Code tool."""
        if tool_name not in self.schemas:
            return {}
        
        schema = self.schemas[tool_name]
        parameters = {}
        
        # Tool-specific parameter extraction
        if tool_name == "Task":
            parameters = self._extract_task_parameters(request, schema)
        elif tool_name == "Bash":
            parameters = self._extract_bash_parameters(request, schema)
        elif tool_name == "Glob":
            parameters = self._extract_glob_parameters(request, schema)
        elif tool_name == "Grep":
            parameters = self._extract_grep_parameters(request, schema)
        elif tool_name == "LS":
            parameters = self._extract_ls_parameters(request, schema, context)
        elif tool_name == "Read":
            parameters = self._extract_read_parameters(request, schema, context)
        elif tool_name == "Write":
            parameters = self._extract_write_parameters(request, schema, context)
        elif tool_name == "Edit":
            parameters = self._extract_edit_parameters(request, schema, context)
        elif tool_name == "MultiEdit":
            parameters = self._extract_multi_edit_parameters(request, schema, context)
        elif tool_name == "WebFetch":
            parameters = self._extract_web_fetch_parameters(request, schema)
        elif tool_name == "WebSearch":
            parameters = self._extract_web_search_parameters(request, schema)
        elif tool_name == "TodoWrite":
            parameters = self._extract_todo_write_parameters(request, schema)
        
        return parameters
    
    def _extract_task_parameters(self, request: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for Task tool."""
        # Look for agent type mentions
        agent_types = ["general-purpose", "statusline-setup", "output-style-setup"]
        subagent_type = "general-purpose"  # default
        
        for agent_type in agent_types:
            if agent_type in request.lower():
                subagent_type = agent_type
                break
        
        # Extract description (first few words)
        description = " ".join(request.split()[:5])
        
        return {
            "description": description,
            "prompt": request,
            "subagent_type": subagent_type
        }
    
    def _extract_bash_parameters(self, request: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for Bash tool."""
        # Look for command after keywords
        command_keywords = ["run", "execute", "command"]
        command = request
        
        for keyword in command_keywords:
            if keyword in request.lower():
                parts = request.split(keyword, 1)
                if len(parts) > 1:
                    command = parts[1].strip()
                break
        
        # If the extracted command is just a single word that doesn't look like a shell command,
        # it's likely not meant to be executed as a bash command
        command_words = command.strip().split()
        if len(command_words) == 1:
            word = command_words[0].lower()
            # Check if it's obviously not a shell command
            non_commands = {
                "turn", "return", "and", "or", "but", "if", "then", "else",
                "when", "where", "what", "how", "why", "this", "that", "navigation", 
                "implement", "create", "build", "make", "help", "please"
            }
            if word in non_commands:
                # Return empty command to prevent execution
                command = ""
        
        # Look for background execution indicators
        run_in_background = any(word in request.lower() for word in ["background", "async", "detached"])
        
        return {
            "command": command,
            "run_in_background": run_in_background,
            "description": f"Execute: {command[:50]}..."
        }
    
    def _extract_glob_parameters(self, request: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for Glob tool."""
        request_lower = request.lower()
        
        # Look for specific file types
        if "python files" in request_lower:
            pattern = "**/*.py"
        elif "javascript files" in request_lower:
            pattern = "**/*.js"
        elif "json files" in request_lower:
            pattern = "**/*.json"
        elif "yaml files" in request_lower or "yml files" in request_lower:
            pattern = "**/*.{yml,yaml}"
        elif "markdown files" in request_lower:
            pattern = "**/*.md"
        elif "all files" in request_lower:
            pattern = "**/*"
        else:
            # Look for explicit glob patterns
            pattern_match = re.search(r'([*?]+[^\\s]*|[^\\s]*[*?]+|\\*\\*[^\\s]*)', request)
            if pattern_match:
                pattern = pattern_match.group(1)
            else:
                # Look for file extensions
                ext_match = re.search(r'\\.(\\w+)', request)
                if ext_match:
                    pattern = f"**/*.{ext_match.group(1)}"
                else:
                    pattern = "**/*"
        
        return {
            "pattern": pattern
        }
    
    def _extract_grep_parameters(self, request: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for Grep tool."""
        # Extract search pattern (usually in quotes or after "search for")
        pattern = request
        
        # Look for quoted strings
        quote_match = re.search(r'["\']([^"\']+)["\']', request)
        if quote_match:
            pattern = quote_match.group(1)
        else:
            # Look for "search for" pattern
            search_match = re.search(r'search for\\s+([^\\s]+)', request, re.IGNORECASE)
            if search_match:
                pattern = search_match.group(1)
        
        # Check for case insensitive flag
        case_insensitive = any(word in request.lower() for word in ["case insensitive", "ignore case"])
        
        # Check for output mode
        output_mode = "files_with_matches"  # default
        if "show content" in request.lower() or "show lines" in request.lower():
            output_mode = "content"
        elif "count" in request.lower():
            output_mode = "count"
        
        params = {
            "pattern": pattern,
            "output_mode": output_mode
        }
        
        if case_insensitive:
            params["-i"] = True
        
        return params
    
    def _extract_ls_parameters(self, request: str, schema: Dict[str, Any], 
                              context: ToolContext) -> Dict[str, Any]:
        """Extract parameters for LS tool."""
        # Look for path in request
        path = context.current_dir or context.current_path or "."
        
        # Look for specific path mentions
        path_match = re.search(r'(?:in|of|at)\\s+([^\\s]+)', request)
        if path_match:
            path = path_match.group(1)
        
        return {
            "path": path
        }
    
    def _extract_read_parameters(self, request: str, schema: Dict[str, Any], 
                                context: ToolContext) -> Dict[str, Any]:
        """Extract parameters for Read tool."""
        # Look for file path
        file_path = None
        
        # Look for quoted file paths first
        quote_match = re.search(r'["\']([^"\']+)["\']', request)
        if quote_match:
            potential_path = quote_match.group(1)
            # Validate it looks like a reasonable file path
            if '.' in potential_path and ('/' in potential_path or '\\' in potential_path or not ' ' in potential_path):
                file_path = potential_path
        
        # If no quoted path found, look for file extensions with paths
        if not file_path:
            # Match patterns like /path/to/file.ext or file.ext
            file_match = re.search(r'([^\s]+\.[a-zA-Z0-9]+)', request)
            if file_match:
                potential_path = file_match.group(1)
                # Basic validation - avoid matching things like "read file.txt from disk" 
                if not re.match(r'^[a-z]+\.[a-z]+$', potential_path):  # Avoid "file.ext" patterns
                    file_path = potential_path
        
        # If still no path, try to extract from common phrases
        if not file_path:
            # Look for patterns like "read FILENAME" or "show FILENAME"
            filename_patterns = [
                r'(?:read|show|display|view|cat)\s+([^\s]+\.[a-zA-Z0-9]+)',
                r'(?:file|path):\s*([^\s]+\.[a-zA-Z0-9]+)',
                r'([./][^\s]*\.[a-zA-Z0-9]+)'  # Paths starting with . or /
            ]
            
            for pattern in filename_patterns:
                match = re.search(pattern, request, re.IGNORECASE)
                if match:
                    file_path = match.group(1)
                    break
        
        return {
            "file_path": file_path  # Return None if not found, instead of empty string
        }
    
    def _extract_write_parameters(self, request: str, schema: Dict[str, Any], 
                                 context: ToolContext) -> Dict[str, Any]:
        """Extract parameters for Write tool."""
        file_path = None
        content = None
        
        # Pattern 1: Direct content with explicit destination - "write 'content' to file.txt"
        content_to_file_patterns = [
            r'(?:write|save)\s+["\']([^"\']+)["\']\s+(?:to|in)\s+([^\s]+\.[a-zA-Z0-9]+)',
            r'(?:write|save)\s+(.+?)\s+(?:to|in)\s+([^\s]+\.[a-zA-Z0-9]+)',
        ]
        
        for pattern in content_to_file_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                content, file_path = match.groups()
                content = content.strip().strip('"\'')  # Clean up quotes
                break
        
        # Pattern 2: File with content - "create file.txt with 'content'"
        if not file_path:
            file_with_content_patterns = [
                r'(?:create|write|make)\s+([^\s]+\.[a-zA-Z0-9]+)\s+(?:with|containing)\s+["\']([^"\']+)["\']',
                r'(?:create|write|make)\s+([^\s]+\.[a-zA-Z0-9]+)\s+(?:with|containing)\s+(.+)',
            ]
            
            for pattern in file_with_content_patterns:
                match = re.search(pattern, request, re.IGNORECASE)
                if match:
                    file_path, content = match.groups()
                    content = content.strip().strip('"\'')
                    break
        
        # Pattern 3: "save the following to file.py: content"
        if not file_path:
            save_following_match = re.search(r'save\s+(?:the\s+)?following\s+to\s+([^\s:]+(?:\.[a-zA-Z0-9]+)?)\s*:\s*(.+)', request, re.IGNORECASE | re.DOTALL)
            if save_following_match:
                file_path, content = save_following_match.groups()
                content = content.strip()
        
        # Pattern 4: Just file creation - "create file.txt", "make README.md", "write file.py"
        if not file_path:
            file_creation_patterns = [
                r'(?:create|make|write)\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?(?:called\s+)?([^\s]+\.[a-zA-Z0-9]+)',
                r'(?:create|make|write)\s+(?:a\s+)?([A-Z][A-Z0-9]*(?:\.[a-zA-Z0-9]+)?)',  # README, CHANGELOG, etc.
            ]
            
            for pattern in file_creation_patterns:
                match = re.search(pattern, request, re.IGNORECASE)
                if match:
                    file_path = match.group(1)
                    # For file creation without explicit content, provide empty string
                    if content is None:
                        content = ""
                    break
        
        # Pattern 5: Generic file path extraction
        if not file_path:
            # Look for any file with extension
            file_match = re.search(r'([^\s]+\.[a-zA-Z0-9]+)', request)
            if file_match:
                potential_path = file_match.group(1)
                # Avoid matching generic words like "file.txt" or "some.thing"
                if not re.match(r'^[a-z]+\.[a-z]+$', potential_path) and '/' not in potential_path[:-10]:
                    file_path = potential_path
                    if content is None:
                        content = ""
        
        # Content extraction if not found yet
        if file_path and content is None:
            # Look for content in quotes or code blocks
            content_patterns = [
                r'```([^`]+)```',  # Code blocks
                r'["\']([^"\']{2,})["\']',  # Quoted strings (reduced min length)
                r'content[:\s]+["\']([^"\']+)["\']',  # Explicit content: "..."
                r':\s*(.+)$',  # Content after colon at end
            ]
            
            for pattern in content_patterns:
                match = re.search(pattern, request, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    break
            
            # If still no content, default to empty string for file creation
            if content is None:
                content = ""
        
        return {
            "file_path": file_path,
            "content": content
        }
    
    def _extract_edit_parameters(self, request: str, schema: Dict[str, Any], 
                                context: ToolContext) -> Dict[str, Any]:
        """Extract parameters for Edit tool."""
        # Look for "replace X with Y" patterns
        replace_match = re.search(r'replace\\s+["\']([^"\']+)["\']\\s+with\\s+["\']([^"\']+)["\']', request, re.IGNORECASE)
        if replace_match:
            return {
                "file_path": "",
                "old_string": replace_match.group(1),
                "new_string": replace_match.group(2)
            }
        
        return {
            "file_path": "",
            "old_string": "",
            "new_string": ""
        }
    
    def _extract_multi_edit_parameters(self, request: str, schema: Dict[str, Any], 
                                      context: ToolContext) -> Dict[str, Any]:
        """Extract parameters for MultiEdit tool."""
        return {
            "file_path": "",
            "edits": []
        }
    
    def _extract_web_fetch_parameters(self, request: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for WebFetch tool."""
        # Look for URLs
        url_match = re.search(r'https?://[^\\s]+', request)
        if url_match:
            url = url_match.group(0)
        else:
            # Look for domain patterns
            domain_match = re.search(r'\\b([a-zA-Z0-9-]+\\.)+[a-zA-Z]{2,}\\b', request)
            url = domain_match.group(0) if domain_match else ""
        
        # The prompt is usually the whole request minus the URL
        prompt = request.replace(url, "").strip() if url else request
        
        return {
            "url": url,
            "prompt": prompt or "Fetch and summarize content"
        }
    
    def _extract_web_search_parameters(self, request: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for WebSearch tool."""
        # Remove search keywords to get the actual query
        query = request
        search_keywords = ["search for", "search", "find", "look up"]
        
        for keyword in search_keywords:
            if request.lower().startswith(keyword):
                query = request[len(keyword):].strip()
                break
        
        return {
            "query": query
        }
    
    def _extract_todo_write_parameters(self, request: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for TodoWrite tool."""
        # This tool typically needs structured input, so return empty for natural language
        return {
            "todos": []
        }
    
    def validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        DEPRECATED: Use unified_validator for enhanced security and validation.
        
        This method is maintained for backward compatibility but should not be used
        for new code. It has known security issues and validation gaps.
        """
        import warnings
        warnings.warn(
            "ClaudeCodeRegistry.validate_parameters is deprecated. "
            "Use unified_validator.validate_tool_parameters for enhanced security.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Use unified validator if available
        try:
            from ..base.unified_validation import unified_validator
            validation_result = unified_validator.validate_tool_parameters(tool_name, parameters)
            return {
                "valid": validation_result.valid,
                "parameters": validation_result.parameters,
                "error": validation_result.get_user_friendly_error() if not validation_result.valid else None,
                "warnings": validation_result.warnings,
                "security_validated": True
            }
        except ImportError:
            # Fallback to legacy validation with warnings
            pass
        
        if tool_name not in self.schemas:
            return {"valid": True, "parameters": parameters, "security_validated": False}
        
        schema = self.schemas[tool_name]
        required_fields = schema.get("required", [])
        
        # Enhanced validation logic
        missing_fields = []
        invalid_fields = []
        
        for field in required_fields:
            if field not in parameters:
                missing_fields.append(field)
            elif parameters[field] is None:
                missing_fields.append(f"{field} (cannot be None)")
            elif isinstance(parameters[field], str) and not parameters[field].strip():
                missing_fields.append(f"{field} (cannot be empty)")
            elif isinstance(parameters[field], str) and len(parameters[field]) > 10000:
                invalid_fields.append(f"{field} (too long: {len(parameters[field])} chars)")
        
        if missing_fields or invalid_fields:
            errors = []
            if missing_fields:
                errors.append(f"Missing or empty required fields: {', '.join(missing_fields)}")
            if invalid_fields:
                errors.append(f"Invalid field values: {', '.join(invalid_fields)}")
            
            return {
                "valid": False,
                "error": "; ".join(errors),
                "parameters": parameters,
                "security_validated": False
            }
        
        return {"valid": True, "parameters": parameters, "security_validated": False}


# Global registry instance
claude_code_registry = ClaudeCodeRegistry()