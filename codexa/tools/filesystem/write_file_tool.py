"""
Write File Tool for Codexa.
"""

from pathlib import Path
from typing import Set
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class WriteFileTool(Tool):
    """Tool for writing/creating files with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Create a new file or overwrite existing file with content"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"write", "create", "file_access", "content_creation"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path", "content"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit write requests
        if any(phrase in request_lower for phrase in [
            "write file", "create file", "save file", "write to file",
            "create new file", "generate file", "output to file"
        ]):
            return 0.9
        
        # Medium confidence for file creation patterns
        if any(phrase in request_lower for phrase in [
            "write", "create", "save", "generate"
        ]) and re.search(r'\.(py|js|ts|json|md|txt|yaml|yml|css|html)', request_lower):
            return 0.7
        
        # Medium confidence for creation keywords
        if any(word in request_lower for word in ["create", "generate", "build", "make"]):
            return 0.4
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file writing."""
        try:
            # Get parameters from context
            file_path = context.get_state("file_path")
            content = context.get_state("content")
            
            # Try to extract from request if not in context
            if not file_path or not content:
                extracted = self._extract_file_and_content(context.user_request)
                file_path = file_path or extracted.get("file_path")
                content = content or extracted.get("content")
            
            if not file_path:
                return ToolResult.error_result(
                    error="No file path specified",
                    tool_name=self.name
                )
            
            if not content:
                return ToolResult.error_result(
                    error="No content specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            if await self._write_with_mcp(file_path, content, context):
                return ToolResult.success_result(
                    data={"path": file_path, "bytes_written": len(content), "source": "mcp"},
                    tool_name=self.name,
                    files_created=[file_path],
                    output=f"Created file: {file_path} (via MCP)"
                )
            
            # Fallback to local filesystem
            await self._write_with_local(file_path, content)
            return ToolResult.success_result(
                data={"path": file_path, "bytes_written": len(content), "source": "local"},
                tool_name=self.name,
                files_created=[file_path],
                output=f"Created file: {file_path} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to write file: {str(e)}",
                tool_name=self.name
            )
    
    async def _write_with_mcp(self, file_path: str, content: str, context: ToolContext) -> bool:
        """Try to write file using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return False
            
            # Import MCP filesystem
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return False
            
            result = await mcp_fs.write_file(file_path, content)
            return result
            
        except Exception as e:
            self.logger.debug(f"MCP write failed: {e}")
            return False
    
    async def _write_with_local(self, file_path: str, content: str) -> None:
        """Write file using local filesystem."""
        path = Path(file_path)
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        path.write_text(content, encoding='utf-8')
    
    def _extract_file_and_content(self, request: str) -> dict:
        """Extract file path and content from request string."""
        result = {"file_path": "", "content": ""}
        
        # Look for file paths with extensions
        file_pattern = r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        file_matches = re.findall(file_pattern, request)
        if file_matches:
            result["file_path"] = file_matches[0]
        
        # Look for quoted content
        content_patterns = [
            r'content[:\s]*["\']([^"\']+)["\']',
            r'with[:\s]*["\']([^"\']+)["\']',
            r'```([^`]+)```',  # Code blocks
            r'["\']([^"\']{20,})["\']'  # Long quoted strings
        ]
        
        for pattern in content_patterns:
            matches = re.findall(pattern, request, re.DOTALL | re.IGNORECASE)
            if matches:
                result["content"] = matches[0].strip()
                break
        
        return result