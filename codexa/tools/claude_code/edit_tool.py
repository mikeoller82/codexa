"""
Edit tool - Performs exact string replacements in files.
"""

import os
from pathlib import Path
from typing import Set, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class EditTool(Tool):
    """Performs exact string replacements in files."""
    
    @property
    def name(self) -> str:
        return "Edit"
    
    @property
    def description(self) -> str:
        return "Performs exact string replacements in files with read-before-edit validation"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return set()  # No required context - will extract from request or ask
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit edit operations
        if any(phrase in request_lower for phrase in [
            "edit file", "modify file", "replace in file", "change in file"
        ]):
            return 0.9
        
        # Medium confidence for replacement operations
        if any(phrase in request_lower for phrase in [
            "replace", "change", "modify", "update", "fix"
        ]) and any(phrase in request_lower for phrase in [
            "file", "code", "text"
        ]):
            return 0.7
        
        return 0.0

    async def validate_context(self, context: ToolContext) -> bool:
        """
        Validate that context contains required information.
        Override base method to handle edit parameters more flexibly.
        """
        # Try to determine parameters from various sources
        file_path = (
            context.get_state("file_path") or
            getattr(context, 'file_path', None)
        )
        old_string = context.get_state("old_string")
        new_string = context.get_state("new_string")

        # If we can determine all parameters, context is valid
        if file_path and old_string is not None and new_string is not None:
            return True

        # If missing parameters, check if we can extract from request
        if context.user_request:
            # For simplicity, allow execute method to handle extraction
            return True

        return True

    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the Edit tool."""
        try:
            # Extract parameters
            file_path = context.get_state("file_path")
            old_string = context.get_state("old_string")
            new_string = context.get_state("new_string")
            replace_all = context.get_state("replace_all", False)
            
            if not all([file_path, old_string is not None, new_string is not None]):
                return ToolResult.error_result(
                    error="Missing required parameters: file_path, old_string, new_string",
                    tool_name=self.name
                )
            
            if old_string == new_string:
                return ToolResult.error_result(
                    error="old_string and new_string cannot be the same",
                    tool_name=self.name
                )
            
            # Convert to Path object
            target_path = Path(file_path)
            
            if not target_path.exists():
                return ToolResult.error_result(
                    error=f"File does not exist: {file_path}",
                    tool_name=self.name
                )
            
            if not target_path.is_file():
                return ToolResult.error_result(
                    error=f"Path is not a file: {file_path}",
                    tool_name=self.name
                )
            
            # Claude Code requirement: Must have read the file first
            if not self._has_file_been_read(file_path, context):
                return ToolResult.error_result(
                    error="Cannot edit file without reading it first (use Read tool first)",
                    tool_name=self.name
                )
            
            # Read current file content
            try:
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                return ToolResult.error_result(
                    error=f"Failed to read file for editing: {str(e)}",
                    tool_name=self.name
                )
            
            # Perform replacement
            if replace_all:
                # Replace all occurrences
                if old_string not in content:
                    return ToolResult.error_result(
                        error=f"String not found in file: '{old_string}'",
                        tool_name=self.name
                    )
                
                new_content = content.replace(old_string, new_string)
                replacement_count = content.count(old_string)
                
            else:
                # Replace only first occurrence, but check uniqueness
                occurrences = content.count(old_string)
                
                if occurrences == 0:
                    return ToolResult.error_result(
                        error=f"String not found in file: '{old_string}'",
                        tool_name=self.name
                    )
                elif occurrences > 1:
                    return ToolResult.error_result(
                        error=f"String appears {occurrences} times in file. Use replace_all=true or provide more context to make it unique",
                        tool_name=self.name
                    )
                
                new_content = content.replace(old_string, new_string, 1)
                replacement_count = 1
            
            # Write the modified content
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                return ToolResult.success_result(
                    data={
                        "file_path": str(target_path.resolve()),
                        "old_string": old_string,
                        "new_string": new_string,
                        "replacement_count": replacement_count,
                        "replace_all": replace_all,
                        "content_length": len(new_content),
                        "line_count": len(new_content.splitlines())
                    },
                    tool_name=self.name,
                    output=f"File edited successfully: {target_path.name} ({replacement_count} replacement{'s' if replacement_count != 1 else ''})",
                    files_modified=[str(target_path)]
                )
                
            except Exception as e:
                return ToolResult.error_result(
                    error=f"Failed to write edited file: {str(e)}",
                    tool_name=self.name
                )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Edit tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _has_file_been_read(self, file_path: str, context: ToolContext) -> bool:
        """Check if the file has been read in this context (Claude Code requirement)."""
        # Check if Read tool has been used for this file in the context
        if hasattr(context, 'previous_results'):
            for tool_name, result in context.previous_results.items():
                if tool_name == "Read" and hasattr(result, 'data') and isinstance(result.data, dict):
                    read_file_path = result.data.get('file_path')
                    if read_file_path and Path(read_file_path).resolve() == Path(file_path).resolve():
                        return True
        
        # Also check shared state for read operations
        read_files = context.get_state("read_files", set())
        return str(Path(file_path).resolve()) in read_files


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to modify"
        },
        "old_string": {
            "type": "string",
            "description": "The text to replace"
        },
        "new_string": {
            "type": "string",
            "description": "The text to replace it with (must be different from old_string)"
        },
        "replace_all": {
            "type": "boolean",
            "default": False,
            "description": "Replace all occurrences of old_string (default false)"
        }
    },
    "required": ["file_path", "old_string", "new_string"],
    "additionalProperties": False
}