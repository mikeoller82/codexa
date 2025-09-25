"""
Basic Read Tool for Codexa.
Provides file reading functionality.
"""

import os
from pathlib import Path
from typing import Set, Dict, Any

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ReadTool(Tool):
    """Tool for reading files."""

    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Read file contents and display file information"

    @property
    def category(self) -> str:
        return "filesystem"

    @property
    def capabilities(self) -> Set[str]:
        return {"file_read", "file_contents", "file_info"}

    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()

        # High confidence for explicit read requests
        if any(phrase in request_lower for phrase in [
            "read file", "read ", "show file", "display file", "cat "
        ]):
            return 0.9

        # Medium confidence for file operations
        if any(keyword in request_lower for keyword in [
            "file", "contents", "view", "open"
        ]):
            return 0.6

        return 0.0

    async def execute(self, context: ToolContext) -> ToolResult:
        """Read file."""
        try:
            # First try to get file path from context state (set by tool manager)
            file_path = context.get_state("file_path")

            # If not in context state, extract from request
            if not file_path:
                file_path = self._extract_file_path(context.user_request)

            if not file_path:
                return ToolResult.error_result(
                    error="No file path found in request",
                    tool_name=self.name
                )

            # Read file
            result = await self._read_file(file_path)

            return ToolResult.success_result(
                data=result,
                tool_name=self.name,
                output=f"Read file: {file_path}"
            )

        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to read file: {str(e)}",
                tool_name=self.name
            )

    def _extract_file_path(self, request: str) -> str:
        """Extract file path from request string."""
        import re

        # Look for file paths in quotes
        patterns = [
            r'["\']([^"\']+)["\']',  # Quoted paths
            r'file\s+([^\s]+)',      # "file path"
            r'read\s+([^\s]+)',      # "read path"
            r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'  # Files with extensions
        ]

        for pattern in patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                return matches[0]

        return ""

    async def _read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file and return contents."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Read file contents
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # Get file info
        stat = path.stat()

        return {
            "path": str(path.absolute()),
            "name": path.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "content": content,
            "lines": len(content.splitlines()),
            "encoding": "utf-8"
        }