"""
Write tool - Writes a file to the local filesystem.
"""

import os
from pathlib import Path
from typing import Set
from ..base.tool_interface import Tool, ToolContext, ToolResult


class WriteTool(Tool):
    """Writes a file to the local filesystem."""
    
    # Claude Code schema compatibility
    CLAUDE_CODE_SCHEMA = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to write (must be absolute, not relative)"
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file"
            }
        },
        "required": ["file_path", "content"],
        "additionalProperties": False
    }
    
    @property
    def name(self) -> str:
        return "Write"
    
    @property
    def description(self) -> str:
        return "Writes a file to the local filesystem, overwriting existing files"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path", "content"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit write operations
        if any(phrase in request_lower for phrase in [
            "write file", "create file", "save file", "write to file"
        ]):
            return 0.9
        
        # Medium confidence for file creation
        if any(phrase in request_lower for phrase in [
            "create", "save", "write", "output to"
        ]) and any(phrase in request_lower for phrase in [
            "file", ".py", ".js", ".md", ".txt", ".json"
        ]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the Write tool."""
        try:
            # Extract parameters
            file_path = context.get_state("file_path")
            content = context.get_state("content")
            
            if not file_path:
                return ToolResult.error_result(
                    error="Missing required parameter: file_path",
                    tool_name=self.name
                )
            
            if content is None:
                return ToolResult.error_result(
                    error="Missing required parameter: content",
                    tool_name=self.name
                )
            
            # Convert to Path object
            target_path = Path(file_path)
            
            # Check if this is an existing file (Claude Code requirement)
            if target_path.exists():
                # Claude Code requires Read tool to be used before Write on existing files
                # We'll check if file has been read in this context
                if not self._has_file_been_read(file_path, context):
                    return ToolResult.error_result(
                        error="Cannot write to existing file without reading it first (use Read tool first)",
                        tool_name=self.name
                    )
            
            # Create parent directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the file
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Get file info
                file_size = target_path.stat().st_size
                line_count = len(content.splitlines())
                
                return ToolResult.success_result(
                    data={
                        "file_path": str(target_path.resolve()),
                        "content_length": len(content),
                        "line_count": line_count,
                        "file_size": file_size,
                        "created": not target_path.existed_before_write if hasattr(target_path, 'existed_before_write') else False
                    },
                    tool_name=self.name,
                    output=f"File written successfully: {target_path.name} ({line_count} lines, {file_size} bytes)",
                    files_created=[str(target_path)] if not target_path.exists() else [],
                    files_modified=[str(target_path)] if target_path.exists() else []
                )
                
            except PermissionError:
                return ToolResult.error_result(
                    error=f"Permission denied writing to file: {file_path}",
                    tool_name=self.name
                )
            except OSError as e:
                return ToolResult.error_result(
                    error=f"OS error writing file: {str(e)}",
                    tool_name=self.name
                )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Write tool execution failed: {str(e)}",
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


