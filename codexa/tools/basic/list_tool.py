"""
Basic List Tool for Codexa.
Provides directory listing functionality.
"""

import os
from pathlib import Path
from typing import Set, Dict, Any

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ListTool(Tool):
    """Tool for listing directory contents."""

    @property
    def name(self) -> str:
        return "list"

    @property
    def description(self) -> str:
        return "List directory contents and file information"

    @property
    def category(self) -> str:
        return "filesystem"

    @property
    def capabilities(self) -> Set[str]:
        return {"directory_listing", "file_discovery", "navigation"}

    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()

        # High confidence for explicit list requests
        if any(phrase in request_lower for phrase in [
            "list directory", "list files", "ls ", "dir ", "show files"
        ]):
            return 0.9

        # Medium confidence for directory operations
        if any(keyword in request_lower for keyword in [
            "directory", "folder", "contents", "files"
        ]):
            return 0.6

        return 0.0

    async def execute(self, context: ToolContext) -> ToolResult:
        """List directory contents."""
        try:
            # First try to get directory path from context state (set by tool manager)
            directory_path = context.get_state("directory_path")

            # If not in context state, extract from request
            if not directory_path:
                directory_path = self._extract_directory_path(context.user_request)

            if not directory_path:
                directory_path = "."

            # List directory
            result = await self._list_directory(directory_path)

            return ToolResult.success_result(
                data=result,
                tool_name=self.name,
                output=f"Listed directory: {directory_path}"
            )

        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to list directory: {str(e)}",
                tool_name=self.name
            )

    def _extract_directory_path(self, request: str) -> str:
        """Extract directory path from request string."""
        import re

        # Look for directory patterns
        patterns = [
            r'["\']([^"\']+)["\']',  # Quoted paths
            r'directory\s+([^\s]+)',  # "directory path"
            r'folder\s+([^\s]+)',     # "folder path"
            r'ls\s+([^\s]+)',         # "ls path"
            r'([a-zA-Z0-9_/.-]+/)',  # Paths ending with /
        ]

        for pattern in patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                return matches[0]

        return ""

    async def _list_directory(self, directory_path: str) -> Dict[str, Any]:
        """List directory contents."""
        path = Path(directory_path)

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")

        entries = []

        # List directory contents
        for item in path.iterdir():
            try:
                stat = item.stat()
                entry = {
                    "name": item.name,
                    "path": str(item.absolute()),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": stat.st_mtime,
                    "is_hidden": item.name.startswith('.'),
                    "extension": item.suffix.lower() if item.is_file() else None
                }
                entries.append(entry)
            except PermissionError:
                # Skip entries we can't access
                continue

        # Sort entries: directories first, then by name
        entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))

        return {
            "path": str(path.absolute()),
            "name": path.name,
            "entry_count": len(entries),
            "entries": entries
        }