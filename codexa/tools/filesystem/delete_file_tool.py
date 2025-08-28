"""
Delete File Tool for Codexa.
"""

from pathlib import Path
from typing import Set
import shutil
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class DeleteFileTool(Tool):
    """Tool for deleting files and directories with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "delete_file"
    
    @property
    def description(self) -> str:
        return "Delete a file or directory from the file system"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"delete", "remove", "cleanup", "file_management"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit delete requests with file/directory context
        import re
        if any(re.search(pattern, request_lower) for pattern in [
            r'\bdelete\s+file\b', r'\bdelete\s+directory\b', 
            r'\bremove\s+file\b', r'\bremove\s+directory\b',
            r'\brm\s+', r'\bdel\s+'
        ]):
            return 0.9
            
        # Medium confidence for delete with file path context
        if ("delete" in request_lower or "remove" in request_lower) and (
            "/" in request or "\\" in request or 
            any(ext in request_lower for ext in [".py", ".js", ".txt", ".md", ".json", ".yml", ".yaml"]) or
            context.get_state("file_path")
        ):
            return 0.7
        
        # Lower confidence for cleanup requests
        if any(phrase in request_lower for phrase in [
            "clean up", "cleanup", "clear"
        ]):
            return 0.3
        
        # Do not handle generic requests
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file/directory deletion."""
        try:
            # Early validation - should not be called for inappropriate requests
            if not self._is_valid_delete_request(context.user_request, context):
                return ToolResult.error_result(
                    error="This tool should not handle this type of request",
                    tool_name=self.name
                )
            
            # Get parameters from context
            file_path = context.get_state("file_path")
            recursive = context.get_state("recursive", False)
            
            # Try to extract from request if not in context
            if not file_path:
                extracted = self._extract_delete_parameters(context.user_request)
                file_path = extracted.get("file_path")
                recursive = extracted.get("recursive", recursive)
            
            if not file_path:
                return ToolResult.error_result(
                    error="No file path specified for deletion",
                    tool_name=self.name
                )
            
            # Safety check - don't delete system paths
            if self._is_dangerous_path(file_path):
                return ToolResult.error_result(
                    error=f"Refusing to delete dangerous path: {file_path}",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            if await self._delete_with_mcp(file_path, recursive, context):
                return ToolResult.success_result(
                    data={"deleted_path": file_path, "recursive": recursive, "method": "mcp"},
                    tool_name=self.name,
                    output=f"Deleted: {file_path} (via MCP)"
                )
            
            # Fallback to local filesystem
            await self._delete_with_local(file_path, recursive)
            return ToolResult.success_result(
                data={"deleted_path": file_path, "recursive": recursive, "method": "local"},
                tool_name=self.name,
                output=f"Deleted: {file_path} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to delete: {str(e)}",
                tool_name=self.name
            )
    
    async def _delete_with_mcp(self, file_path: str, recursive: bool, context: ToolContext) -> bool:
        """Try to delete using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return False
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return False
            
            result = await mcp_fs.delete_file(file_path, recursive)
            return result
            
        except Exception as e:
            self.logger.debug(f"MCP delete failed: {e}")
            return False
    
    async def _delete_with_local(self, file_path: str, recursive: bool) -> None:
        """Delete using local filesystem."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {file_path}")
        
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()  # Will fail if directory is not empty
        else:
            raise ValueError(f"Unknown file type: {file_path}")
    
    def _extract_delete_parameters(self, request: str) -> dict:
        """Extract deletion parameters from request."""
        result = {"file_path": "", "recursive": False}
        
        # Check for recursive flag
        if any(word in request.lower() for word in ["recursive", "-r", "--recursive", "all"]):
            result["recursive"] = True
        
        # Look for file paths
        file_patterns = [
            r'delete\s+([^\s]+)',
            r'remove\s+([^\s]+)',
            r'rm\s+([^\s]+)',
            r'del\s+([^\s]+)'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["file_path"] = matches[0]
                break
        
        return result
    
    def _is_dangerous_path(self, path: str) -> bool:
        """Check if path is dangerous to delete."""
        dangerous_paths = {
            "/", "/bin", "/sbin", "/usr", "/etc", "/var", "/boot", "/sys", "/proc",
            "C:\\", "C:\\Windows", "C:\\Program Files", "C:\\Users",
            "/System", "/Applications", "/Library",
            "~", "/home", "/Users"
        }
        
        # Normalize path
        normalized = Path(path).resolve()
        
        # Check against dangerous paths
        for dangerous in dangerous_paths:
            try:
                dangerous_path = Path(dangerous).resolve()
                if normalized == dangerous_path or dangerous_path in normalized.parents:
                    return True
            except:
                continue
        
        return False
    
    def _is_valid_delete_request(self, request: str, context: ToolContext) -> bool:
        """Validate that this is actually a delete request that should be handled by this tool."""
        if not request:
            return False
            
        request_lower = request.lower()
        
        # Must contain explicit delete/remove terms
        if not any(term in request_lower for term in ["delete", "remove", "rm ", "del ", "cleanup", "clean"]):
            return False
        
        # Should have file/directory context indicators
        has_path_indicators = (
            "/" in request or "\\" in request or  # Path separators
            any(ext in request_lower for ext in [".py", ".js", ".txt", ".md", ".json", ".yml", ".yaml"]) or  # File extensions
            context.get_state("file_path") or  # Explicit file path in context
            any(term in request_lower for term in ["file", "directory", "folder"])  # File/directory keywords
        )
        
        return has_path_indicators