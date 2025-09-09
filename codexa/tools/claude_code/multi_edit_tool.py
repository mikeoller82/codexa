"""
MultiEdit tool - Makes multiple edits to a single file in one operation.
"""

import os
from pathlib import Path
from typing import Set, List, Dict, Any
from ..base.tool_interface import Tool, ToolContext, ToolResult


class MultiEditTool(Tool):
    """Makes multiple edits to a single file in one operation."""
    
    @property
    def name(self) -> str:
        return "MultiEdit"
    
    @property
    def description(self) -> str:
        return "Makes multiple find-and-replace operations on a single file efficiently"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path", "edits"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit multi-edit operations
        if any(phrase in request_lower for phrase in [
            "multiple edit", "batch edit", "several changes", "multiple replace"
        ]):
            return 0.9
        
        # Medium confidence for multiple modifications
        if any(phrase in request_lower for phrase in [
            "multiple", "several", "many", "batch"
        ]) and any(phrase in request_lower for phrase in [
            "edit", "change", "replace", "modify"
        ]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the MultiEdit tool."""
        try:
            # Extract parameters
            file_path = context.get_state("file_path")
            edits = context.get_state("edits")
            
            if not file_path:
                return ToolResult.error_result(
                    error="Missing required parameter: file_path",
                    tool_name=self.name
                )
            
            if not edits or not isinstance(edits, list):
                return ToolResult.error_result(
                    error="Missing or invalid required parameter: edits (must be a list)",
                    tool_name=self.name
                )
            
            if len(edits) == 0:
                return ToolResult.error_result(
                    error="At least one edit operation is required",
                    tool_name=self.name
                )
            
            # Validate edit operations
            for i, edit in enumerate(edits):
                if not isinstance(edit, dict):
                    return ToolResult.error_result(
                        error=f"Edit {i+1} must be a dictionary",
                        tool_name=self.name
                    )
                
                if "old_string" not in edit or "new_string" not in edit:
                    return ToolResult.error_result(
                        error=f"Edit {i+1} must have 'old_string' and 'new_string' fields",
                        tool_name=self.name
                    )
                
                if edit["old_string"] == edit["new_string"]:
                    return ToolResult.error_result(
                        error=f"Edit {i+1}: old_string and new_string cannot be the same",
                        tool_name=self.name
                    )
            
            # Convert to Path object
            target_path = Path(file_path)
            
            # Handle new file creation (first edit with empty old_string)
            is_new_file = False
            if not target_path.exists():
                if len(edits) > 0 and edits[0].get("old_string") == "":
                    is_new_file = True
                    # Create parent directory if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    return ToolResult.error_result(
                        error=f"File does not exist: {file_path}",
                        tool_name=self.name
                    )
            
            if target_path.exists() and not target_path.is_file():
                return ToolResult.error_result(
                    error=f"Path is not a file: {file_path}",
                    tool_name=self.name
                )
            
            # Claude Code requirement: Must have read the file first (unless new file)
            if not is_new_file and not self._has_file_been_read(file_path, context):
                return ToolResult.error_result(
                    error="Cannot edit existing file without reading it first (use Read tool first)",
                    tool_name=self.name
                )
            
            # Read current content (empty for new files)
            if is_new_file:
                content = ""
            else:
                try:
                    with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    return ToolResult.error_result(
                        error=f"Failed to read file for editing: {str(e)}",
                        tool_name=self.name
                    )
            
            # Apply edits in sequence
            edit_results = []
            current_content = content
            
            for i, edit in enumerate(edits):
                old_string = edit["old_string"]
                new_string = edit["new_string"]
                replace_all = edit.get("replace_all", False)
                
                # Handle file creation (empty old_string for first edit)
                if i == 0 and is_new_file and old_string == "":
                    current_content = new_string
                    edit_results.append({
                        "edit_number": i + 1,
                        "old_string": old_string,
                        "new_string": new_string,
                        "replacement_count": 1,
                        "operation": "create_file"
                    })
                    continue
                
                # Normal edit operation
                if replace_all:
                    # Replace all occurrences
                    if old_string not in current_content:
                        return ToolResult.error_result(
                            error=f"Edit {i+1}: String not found in file: '{old_string}'",
                            tool_name=self.name
                        )
                    
                    replacement_count = current_content.count(old_string)
                    current_content = current_content.replace(old_string, new_string)
                    
                else:
                    # Replace only first occurrence, but check uniqueness
                    occurrences = current_content.count(old_string)
                    
                    if occurrences == 0:
                        return ToolResult.error_result(
                            error=f"Edit {i+1}: String not found in file: '{old_string}'",
                            tool_name=self.name
                        )
                    elif occurrences > 1:
                        return ToolResult.error_result(
                            error=f"Edit {i+1}: String appears {occurrences} times. Use replace_all=true or provide more context",
                            tool_name=self.name
                        )
                    
                    current_content = current_content.replace(old_string, new_string, 1)
                    replacement_count = 1
                
                edit_results.append({
                    "edit_number": i + 1,
                    "old_string": old_string,
                    "new_string": new_string,
                    "replacement_count": replacement_count,
                    "replace_all": replace_all
                })
            
            # Write the final content
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(current_content)
                
                total_replacements = sum(result["replacement_count"] for result in edit_results)
                
                return ToolResult.success_result(
                    data={
                        "file_path": str(target_path.resolve()),
                        "edit_count": len(edits),
                        "total_replacements": total_replacements,
                        "edit_results": edit_results,
                        "content_length": len(current_content),
                        "line_count": len(current_content.splitlines()),
                        "is_new_file": is_new_file
                    },
                    tool_name=self.name,
                    output=f"MultiEdit completed: {target_path.name} ({len(edits)} edits, {total_replacements} total replacements)",
                    files_created=[str(target_path)] if is_new_file else [],
                    files_modified=[str(target_path)] if not is_new_file else []
                )
                
            except Exception as e:
                return ToolResult.error_result(
                    error=f"Failed to write edited file: {str(e)}",
                    tool_name=self.name
                )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"MultiEdit tool execution failed: {str(e)}",
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
        "edits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "old_string": {
                        "type": "string",
                        "description": "The text to replace"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The text to replace it with"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "default": False,
                        "description": "Replace all occurrences of old_string"
                    }
                },
                "required": ["old_string", "new_string"],
                "additionalProperties": False
            },
            "minItems": 1,
            "description": "Array of edit operations to perform sequentially on the file"
        }
    },
    "required": ["file_path", "edits"],
    "additionalProperties": False
}