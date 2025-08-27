"""
Create Directory Tool for Codexa.
"""

from pathlib import Path
from typing import Set
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class CreateDirectoryTool(Tool):
    """Tool for creating directories with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "create_directory"
    
    @property
    def description(self) -> str:
        return "Create a new directory or ensure a directory exists"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"create", "mkdir", "directory_management"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"directory_path"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit directory creation
        if any(phrase in request_lower for phrase in [
            "create directory", "create folder", "make directory", "make folder",
            "mkdir", "create dir", "new directory", "new folder"
        ]):
            return 0.9
        
        # Medium confidence for creation keywords with directory context
        if any(word in request_lower for word in ["create", "make", "build"]) and \
           any(word in request_lower for word in ["directory", "folder", "dir"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute directory creation."""
        try:
            # Get directory path from context
            directory_path = context.get_state("directory_path")
            parents = context.get_state("parents", True)  # Create parent dirs by default
            
            # Try to extract from request if not in context
            if not directory_path:
                directory_path = self._extract_directory_path(context.user_request)
            
            if not directory_path:
                return ToolResult.error_result(
                    error="No directory path specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            if await self._create_with_mcp(directory_path, context):
                return ToolResult.success_result(
                    data={"directory_path": directory_path, "method": "mcp"},
                    tool_name=self.name,
                    output=f"Created directory: {directory_path} (via MCP)"
                )
            
            # Fallback to local filesystem
            await self._create_with_local(directory_path, parents)
            return ToolResult.success_result(
                data={"directory_path": directory_path, "method": "local"},
                tool_name=self.name,
                output=f"Created directory: {directory_path} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to create directory: {str(e)}",
                tool_name=self.name
            )
    
    async def _create_with_mcp(self, directory_path: str, context: ToolContext) -> bool:
        """Try to create directory using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return False
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return False
            
            result = await mcp_fs.create_directory(directory_path)
            return result
            
        except Exception as e:
            self.logger.debug(f"MCP create directory failed: {e}")
            return False
    
    async def _create_with_local(self, directory_path: str, parents: bool) -> None:
        """Create directory using local filesystem."""
        path = Path(directory_path)
        
        if path.exists():
            if path.is_dir():
                self.logger.info(f"Directory already exists: {directory_path}")
                return
            else:
                raise FileExistsError(f"Path exists but is not a directory: {directory_path}")
        
        path.mkdir(parents=parents, exist_ok=True)
    
    def _extract_directory_path(self, request: str) -> str:
        """Extract directory path from request."""
        # Look for directory creation patterns
        patterns = [
            r'create\s+(?:directory|folder|dir)\s+([^\s]+)',
            r'make\s+(?:directory|folder|dir)\s+([^\s]+)',
            r'mkdir\s+([^\s]+)',
            r'new\s+(?:directory|folder)\s+([^\s]+)',
            r'["\']([^"\']+)["\']'  # Quoted paths
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return ""