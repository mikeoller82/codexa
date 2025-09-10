"""
Read tool - Reads a file from the local filesystem.
"""

import os
from pathlib import Path
from typing import Set, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class ReadTool(Tool):
    """Reads a file from the local filesystem."""
    
    # Claude Code schema compatibility
    CLAUDE_CODE_SCHEMA = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to read"
            },
            "offset": {
                "type": "number",
                "description": "The line number to start reading from"
            },
            "limit": {
                "type": "number",
                "description": "The number of lines to read"
            }
        },
        "required": ["file_path"],
        "additionalProperties": False
    }
    
    @property
    def name(self) -> str:
        return "Read"
    
    @property
    def description(self) -> str:
        return "Reads a file from the local filesystem with optional line offset and limit"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit read operations
        if any(phrase in request_lower for phrase in [
            "read file", "show file", "display file", "view file", "cat"
        ]):
            return 0.9
        
        # Medium confidence for file content requests
        if any(phrase in request_lower for phrase in [
            "content of", "what's in", "show me", "file contents"
        ]):
            return 0.7
        
        # Lower confidence for general file operations
        if any(phrase in request_lower for phrase in [
            "read", "view", "show", "display"
        ]) and any(phrase in request_lower for phrase in [
            "file", ".py", ".js", ".md", ".txt", ".json"
        ]):
            return 0.5
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the Read tool."""
        try:
            # Extract parameters
            file_path = context.get_state("file_path")
            offset = context.get_state("offset")
            limit = context.get_state("limit", 2000)  # Default 2000 lines
            
            if not file_path:
                return ToolResult.error_result(
                    error="Missing required parameter: file_path",
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
            
            # Check file size and type
            file_size = target_path.stat().st_size
            
            # Handle different file types
            if self._is_binary_file(target_path):
                return self._handle_binary_file(target_path, file_size)
            
            # Read text file
            content, line_count, was_truncated = self._read_text_file(
                target_path, offset, limit
            )
            
            return ToolResult.success_result(
                data={
                    "file_path": str(target_path.resolve()),
                    "content": content,
                    "line_count": line_count,
                    "file_size": file_size,
                    "was_truncated": was_truncated,
                    "offset": offset,
                    "limit": limit
                },
                tool_name=self.name,
                output=self._format_output(content, target_path, line_count, was_truncated, offset)
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Read tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _is_binary_file(self, path: Path) -> bool:
        """Check if file is binary."""
        binary_extensions = {
            '.exe', '.dll', '.so', '.dylib',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
            '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.bin', '.obj', '.o', '.a', '.lib'
        }
        
        if path.suffix.lower() in binary_extensions:
            return True
        
        # Check first few bytes for binary content
        try:
            with open(path, 'rb') as f:
                chunk = f.read(1024)
                # If there are null bytes, it's likely binary
                if b'\x00' in chunk:
                    return True
        except Exception:
            return True
        
        return False
    
    def _handle_binary_file(self, path: Path, file_size: int) -> ToolResult:
        """Handle binary file reading."""
        file_type = "binary"
        
        # Determine specific type based on extension
        ext = path.suffix.lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico']:
            file_type = "image"
        elif ext in ['.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac']:
            file_type = "media"
        elif ext in ['.pdf']:
            file_type = "document"
        elif ext in ['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar']:
            file_type = "archive"
        
        return ToolResult.success_result(
            data={
                "file_path": str(path.resolve()),
                "file_type": file_type,
                "file_size": file_size,
                "is_binary": True
            },
            tool_name=self.name,
            output=f"Binary file ({file_type}): {path.name} ({self._format_file_size(file_size)})"
        )
    
    def _read_text_file(self, path: Path, offset: Optional[int], limit: int) -> tuple:
        """Read text file with optional offset and limit."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            content = None
            encoding_used = None
            
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                        encoding_used = encoding
                        break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError("Could not decode file with any supported encoding")
            
            # Split into lines
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)
            
            # Apply offset and limit
            start_line = offset if offset is not None else 0
            end_line = start_line + limit if limit else total_lines
            
            selected_lines = lines[start_line:end_line]
            was_truncated = end_line < total_lines or limit < total_lines
            
            # Truncate long lines (2000 character limit per line)
            for i, line in enumerate(selected_lines):
                if len(line) > 2000:
                    selected_lines[i] = line[:2000] + "... [line truncated]\n"
            
            # Format with line numbers (cat -n format)
            formatted_lines = []
            for i, line in enumerate(selected_lines):
                line_num = start_line + i + 1
                # Use Claude Code format: spaces + line number + tab
                formatted_lines.append(f"     {line_num}\t{line.rstrip()}")
            
            return '\n'.join(formatted_lines), total_lines, was_truncated
            
        except Exception as e:
            raise Exception(f"Failed to read text file: {str(e)}")
    
    def _format_output(self, content: str, path: Path, line_count: int, 
                      was_truncated: bool, offset: Optional[int]) -> str:
        """Format the file content for display."""
        output_lines = []
        
        # Header with file info
        start_line = offset + 1 if offset is not None else 1
        if was_truncated:
            output_lines.append(f"File: {path.name} (showing lines {start_line}+, {line_count} total lines)")
        else:
            output_lines.append(f"File: {path.name} ({line_count} lines)")
        
        output_lines.append("")
        output_lines.append(content)
        
        if was_truncated:
            output_lines.append("")
            output_lines.append("[Content truncated - use offset and limit parameters to read more]")
        
        return '\n'.join(output_lines)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

