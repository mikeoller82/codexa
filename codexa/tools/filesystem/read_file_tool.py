"""
Read File Tool for Codexa.
"""

from pathlib import Path
from typing import Set
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ReadFileTool(Tool):
    """Tool for reading file contents with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read the complete contents of a file"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"read", "file_access", "content_retrieval"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit read requests
        if any(phrase in request_lower for phrase in [
            "read file", "read the file", "show file content", "display file",
            "open file", "view file", "get file content", "file contents"
        ]):
            return 0.9
        
        # Medium confidence for file access patterns
        if re.search(r'\bread\b.*\.(py|js|ts|json|md|txt|yaml|yml|css|html)', request_lower):
            return 0.7
        
        # Low confidence for general file mentions
        if any(word in request_lower for word in ["file", "content", "show", "display"]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file reading."""
        try:
            # Get file path from context
            file_path = context.get_state("file_path")
            if not file_path:
                # Try to extract from user request
                file_path = self._extract_file_path(context.user_request)
                if not file_path:
                    return ToolResult.error_result(
                        error="No file path specified",
                        tool_name=self.name
                    )
            
            # Try MCP filesystem first
            content = await self._read_with_mcp(file_path, context)
            if content is not None:
                return ToolResult.success_result(
                    data={"content": content, "path": file_path, "source": "mcp"},
                    tool_name=self.name,
                    output=f"Read file: {file_path} (via MCP)"
                )
            
            # Fallback to local filesystem
            content = await self._read_with_local(file_path)
            return ToolResult.success_result(
                data={"content": content, "path": file_path, "source": "local"},
                tool_name=self.name,
                output=f"Read file: {file_path} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to read file: {str(e)}",
                tool_name=self.name
            )
    
    async def _read_with_mcp(self, file_path: str, context: ToolContext) -> str:
        """Try to read file using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            # Import MCP filesystem
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            content = await mcp_fs.read_file(file_path)
            return content
            
        except Exception as e:
            self.logger.debug(f"MCP read failed: {e}")
            return None
    
    async def _read_with_local(self, file_path: str) -> str:
        """Read file using local filesystem."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise IsADirectoryError(f"Path is a directory: {file_path}")
        
        try:
            return path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try other encodings
            for encoding in ['latin-1', 'cp1252', 'ascii']:
                try:
                    return path.read_text(encoding=encoding)
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and decode with errors='ignore'
            return path.read_text(encoding='utf-8', errors='ignore')
    
    def _extract_file_path(self, request: str) -> str:
        """Extract file path from request string."""
        import re
        
        # Look for file paths with extensions
        file_pattern = r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        matches = re.findall(file_pattern, request)
        
        if matches:
            return matches[0]
        
        # Look for quoted paths
        quoted_pattern = r'["\']([^"\']+)["\']'
        matches = re.findall(quoted_pattern, request)
        
        for match in matches:
            if '/' in match or '\\' in match or '.' in match:
                return match
        
        return ""