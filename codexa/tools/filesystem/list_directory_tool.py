"""
List Directory Tool for Codexa.
"""

from pathlib import Path
from typing import Set, List, Dict, Any
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ListDirectoryTool(Tool):
    """Tool for listing directory contents with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "list_directory"
    
    @property
    def description(self) -> str:
        return "Get a detailed listing of all files and directories in a specified path"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"list", "directory", "file_discovery", "navigation"}
    
    @property
    def required_context(self) -> Set[str]:
        return set()  # No required context - directory path is extracted from user request
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit list requests
        if any(phrase in request_lower for phrase in [
            "list directory", "list folder", "show directory", "ls",
            "directory contents", "folder contents", "what's in", "files in"
        ]):
            return 0.9
        
        # Medium confidence for navigation requests
        if any(phrase in request_lower for phrase in [
            "show files", "list files", "directory", "folder", "contents"
        ]):
            return 0.6
        
        # Low confidence for general exploration
        if any(word in request_lower for word in ["list", "show", "display"]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute directory listing."""
        try:
            # Get directory path from context
            directory_path = context.get_state("directory_path")
            if not directory_path:
                # Try to extract from user request
                directory_path = self._extract_directory_path(context.user_request)
                if not directory_path:
                    directory_path = context.current_dir or "."
            
            # Try MCP filesystem first
            mcp_result = await self._list_with_mcp(directory_path, context)
            if mcp_result is not None:
                return ToolResult.success_result(
                    data={"entries": mcp_result, "path": directory_path, "source": "mcp"},
                    tool_name=self.name,
                    output=f"Listed directory: {directory_path} ({len(mcp_result)} entries via MCP)"
                )
            
            # Fallback to local filesystem
            local_result = await self._list_with_local(directory_path)
            return ToolResult.success_result(
                data={"entries": local_result, "path": directory_path, "source": "local"},
                tool_name=self.name,
                output=f"Listed directory: {directory_path} ({len(local_result)} entries local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to list directory: {str(e)}",
                tool_name=self.name
            )
    
    async def _list_with_mcp(self, directory_path: str, context: ToolContext) -> List[Dict[str, Any]]:
        """Try to list directory using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            # Import MCP filesystem
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            entries = await mcp_fs.list_directory(directory_path)
            return entries
            
        except Exception as e:
            self.logger.debug(f"MCP list failed: {e}")
            return None
    
    async def _list_with_local(self, directory_path: str) -> List[Dict[str, Any]]:
        """List directory using local filesystem."""
        path = Path(directory_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")
        
        entries = []
        
        try:
            for item in path.iterdir():
                entry = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": item.stat().st_mtime,
                    "permissions": oct(item.stat().st_mode)[-3:],
                    "is_hidden": item.name.startswith('.'),
                    "extension": item.suffix.lower() if item.is_file() else None
                }
                entries.append(entry)
            
            # Sort entries: directories first, then by name
            entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
            
        except PermissionError:
            raise PermissionError(f"Permission denied: {directory_path}")
        
        return entries
    
    def _extract_directory_path(self, request: str) -> str:
        """Extract directory path from request string."""
        import re
        
        # Look for directory patterns
        directory_patterns = [
            r'in\s+([a-zA-Z0-9_/.-]+)',
            r'directory\s+([a-zA-Z0-9_/.-]+)',
            r'folder\s+([a-zA-Z0-9_/.-]+)',
            r'([a-zA-Z0-9_/.-]+/)',  # Paths ending with /
            r'["\']([^"\']+)["\']'  # Quoted paths
        ]
        
        for pattern in directory_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return ""