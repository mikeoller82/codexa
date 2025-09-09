"""
Glob tool - Fast file pattern matching tool that works with any codebase size.
"""

import glob
import os
from pathlib import Path
from typing import Set, List, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class GlobTool(Tool):
    """Fast file pattern matching tool that works with any codebase size."""
    
    # Claude Code schema compatibility
    CLAUDE_CODE_SCHEMA = {
        "type": "object", 
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The glob pattern to match files against"
            },
            "path": {
                "type": "string", 
                "description": "The directory to search in"
            }
        },
        "required": ["pattern"],
        "additionalProperties": False
    }
    
    @property
    def name(self) -> str:
        return "Glob"
    
    @property
    def description(self) -> str:
        return "Fast file pattern matching tool that supports glob patterns like **/*.js"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"pattern"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit glob patterns
        if any(pattern in request_lower for pattern in [
            "**/*", "*.js", "*.py", "*.md", "*.json", "*.yml", "*.yaml", "*.txt"
        ]):
            return 0.9
        
        # High confidence for glob-related keywords
        if any(phrase in request_lower for phrase in [
            "find files", "pattern match", "glob", "file pattern", "search files"
        ]):
            return 0.8
        
        # Medium confidence for file finding
        if any(phrase in request_lower for phrase in [
            "find", "locate", "search", "files with", "files ending", "python files", "javascript files", "all files"
        ]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the Glob tool."""
        try:
            # Extract parameters
            pattern = context.get_state("pattern")
            path = context.get_state("path")
            
            if not pattern:
                return ToolResult.error_result(
                    error="Missing required parameter: pattern",
                    tool_name=self.name
                )
            
            # Determine search path
            search_path = path or context.current_dir or context.current_path or os.getcwd()
            
            # Convert to Path object for easier handling
            search_path = Path(search_path)
            
            if not search_path.exists():
                return ToolResult.error_result(
                    error=f"Search path does not exist: {search_path}",
                    tool_name=self.name
                )
            
            # Execute glob search
            matching_files = self._glob_search(pattern, search_path)
            
            # Sort by modification time (newest first)
            matching_files = self._sort_by_modification_time(matching_files)
            
            return ToolResult.success_result(
                data={
                    "pattern": pattern,
                    "search_path": str(search_path),
                    "files": matching_files,
                    "count": len(matching_files)
                },
                tool_name=self.name,
                output=self._format_output(matching_files, pattern)
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Glob tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _glob_search(self, pattern: str, search_path: Path) -> List[str]:
        """Perform glob search in the specified path."""
        # Change to search directory for relative patterns
        original_cwd = os.getcwd()
        try:
            os.chdir(search_path)
            
            # Use glob.glob with recursive support
            if "**" in pattern:
                # Recursive search
                matches = glob.glob(pattern, recursive=True)
            else:
                # Non-recursive search
                matches = glob.glob(pattern)
            
            # Convert to absolute paths
            absolute_matches = []
            for match in matches:
                abs_path = (search_path / match).resolve()
                if abs_path.is_file():  # Only include files, not directories
                    absolute_matches.append(str(abs_path))
            
            return absolute_matches
            
        finally:
            os.chdir(original_cwd)
    
    def _sort_by_modification_time(self, files: List[str]) -> List[str]:
        """Sort files by modification time (newest first)."""
        try:
            return sorted(files, key=lambda f: os.path.getmtime(f), reverse=True)
        except OSError:
            # If we can't get modification time, return unsorted
            return files
    
    def _format_output(self, files: List[str], pattern: str) -> str:
        """Format the output for display."""
        if not files:
            return f"No files found matching pattern: {pattern}"
        
        output_lines = [f"Found {len(files)} files matching '{pattern}':"]
        
        # Show up to 20 files to avoid overwhelming output
        display_files = files[:20]
        for file_path in display_files:
            # Show relative path if possible for cleaner output
            try:
                rel_path = os.path.relpath(file_path)
                if len(rel_path) < len(file_path):
                    output_lines.append(f"  {rel_path}")
                else:
                    output_lines.append(f"  {file_path}")
            except ValueError:
                # Can't make relative path, use absolute
                output_lines.append(f"  {file_path}")
        
        if len(files) > 20:
            output_lines.append(f"  ... and {len(files) - 20} more files")
        
        return "\n".join(output_lines)


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "The glob pattern to match files against"
        },
        "path": {
            "type": "string",
            "description": "The directory to search in. If not specified, the current working directory will be used"
        }
    },
    "required": ["pattern"],
    "additionalProperties": False
}