"""
LS tool - Lists files and directories in a given path.
"""

import os
import fnmatch
from pathlib import Path
from typing import Set, List, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class LSTool(Tool):
    """Lists files and directories in a given path."""
    
    @property
    def name(self) -> str:
        return "LS"
    
    @property
    def description(self) -> str:
        return "Lists files and directories in a given path with optional glob pattern filtering"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return set()  # Path can be derived from context
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit listing commands
        if any(phrase in request_lower for phrase in [
            "list files", "list directory", "ls", "dir", "show files"
        ]):
            return 0.9
        
        # Medium confidence for directory exploration
        if any(phrase in request_lower for phrase in [
            "what's in", "contents of", "files in", "explore directory"
        ]):
            return 0.7
        
        # Lower confidence for general listing
        if any(phrase in request_lower for phrase in [
            "list", "show", "directory", "folder"
        ]):
            return 0.4
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the LS tool."""
        try:
            # Extract parameters
            path = context.get_state("path") or context.current_dir or context.current_path or "."
            ignore_patterns = context.get_state("ignore", [])
            
            if not path:
                return ToolResult.error_result(
                    error="Missing required parameter: path",
                    tool_name=self.name
                )
            
            # Convert to Path object
            target_path = Path(path)
            
            if not target_path.exists():
                return ToolResult.error_result(
                    error=f"Path does not exist: {path}",
                    tool_name=self.name
                )
            
            if not target_path.is_dir():
                return ToolResult.error_result(
                    error=f"Path is not a directory: {path}",
                    tool_name=self.name
                )
            
            # List directory contents
            entries = self._list_directory(target_path, ignore_patterns)
            
            return ToolResult.success_result(
                data={
                    "path": str(target_path.resolve()),
                    "entries": entries,
                    "count": len(entries),
                    "ignore_patterns": ignore_patterns
                },
                tool_name=self.name,
                output=self._format_output(entries, target_path)
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"LS tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _list_directory(self, path: Path, ignore_patterns: List[str]) -> List[dict]:
        """List directory contents with type information."""
        entries = []
        
        try:
            for item in path.iterdir():
                # Check if item should be ignored
                if self._should_ignore(item.name, ignore_patterns):
                    continue
                
                try:
                    # Get basic information
                    stat_info = item.stat()
                    
                    entry = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat_info.st_size if item.is_file() else None,
                        "modified": stat_info.st_mtime,
                        "permissions": oct(stat_info.st_mode)[-3:],
                        "path": str(item.resolve())
                    }
                    
                    # Add file extension for files
                    if item.is_file():
                        entry["extension"] = item.suffix
                    
                    entries.append(entry)
                    
                except (OSError, PermissionError) as e:
                    # Add entry for inaccessible items
                    entries.append({
                        "name": item.name,
                        "type": "unknown",
                        "error": str(e),
                        "path": str(item)
                    })
        
        except PermissionError:
            raise PermissionError(f"Permission denied accessing directory: {path}")
        
        # Sort entries: directories first, then files, both alphabetically
        entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        
        return entries
    
    def _should_ignore(self, name: str, ignore_patterns: List[str]) -> bool:
        """Check if a file/directory should be ignored based on patterns."""
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    
    def _format_output(self, entries: List[dict], path: Path) -> str:
        """Format the directory listing for display."""
        if not entries:
            return f"Directory is empty: {path}"
        
        output_lines = [f"Contents of {path}:"]
        output_lines.append("")
        
        # Group by type
        directories = [e for e in entries if e.get("type") == "directory"]
        files = [e for e in entries if e.get("type") == "file"]
        others = [e for e in entries if e.get("type") not in ["directory", "file"]]
        
        # Show directories first
        if directories:
            output_lines.append("Directories:")
            for entry in directories:
                output_lines.append(f"  📁 {entry['name']}/")
        
        # Show files
        if files:
            if directories:
                output_lines.append("")
            output_lines.append("Files:")
            for entry in files:
                size_str = self._format_file_size(entry.get("size", 0))
                ext = entry.get("extension", "")
                icon = self._get_file_icon(ext)
                output_lines.append(f"  {icon} {entry['name']} ({size_str})")
        
        # Show other items (symlinks, special files, etc.)
        if others:
            if directories or files:
                output_lines.append("")
            output_lines.append("Other:")
            for entry in others:
                if "error" in entry:
                    output_lines.append(f"  ❌ {entry['name']} (error: {entry['error']})")
                else:
                    output_lines.append(f"  ❓ {entry['name']}")
        
        # Add summary
        output_lines.append("")
        output_lines.append(f"Total: {len(directories)} directories, {len(files)} files")
        
        return "\n".join(output_lines)
    
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
    
    def _get_file_icon(self, extension: str) -> str:
        """Get appropriate icon for file extension."""
        icon_map = {
            ".py": "🐍",
            ".js": "📜",
            ".ts": "📘",
            ".jsx": "⚛️",
            ".tsx": "⚛️",
            ".md": "📝",
            ".txt": "📄",
            ".json": "📋",
            ".yml": "⚙️",
            ".yaml": "⚙️",
            ".xml": "📄",
            ".html": "🌐",
            ".css": "🎨",
            ".scss": "🎨",
            ".less": "🎨",
            ".sql": "🗃️",
            ".sh": "🖥️",
            ".bat": "🖥️",
            ".exe": "⚙️",
            ".zip": "📦",
            ".tar": "📦",
            ".gz": "📦",
            ".pdf": "📕",
            ".doc": "📘",
            ".docx": "📘",
            ".png": "🖼️",
            ".jpg": "🖼️",
            ".jpeg": "🖼️",
            ".gif": "🖼️",
            ".svg": "🖼️",
            ".mp3": "🎵",
            ".mp4": "🎬",
            ".avi": "🎬",
            ".mov": "🎬"
        }
        
        return icon_map.get(extension.lower(), "📄")


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "The absolute path to the directory to list (must be absolute, not relative)"
        },
        "ignore": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of glob patterns to ignore"
        }
    },
    "required": ["path"],
    "additionalProperties": False
}