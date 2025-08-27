"""
Copy File Tool for Codexa.
"""

from pathlib import Path
from typing import Set
import shutil
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class CopyFileTool(Tool):
    """Tool for copying files and directories with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "copy_file"
    
    @property
    def description(self) -> str:
        return "Copy files and directories"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"copy", "duplicate", "backup", "file_management"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"source", "destination"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit copy requests
        if any(phrase in request_lower for phrase in [
            "copy file", "copy directory", "duplicate file", "copy to",
            "make a copy", "backup file", "cp "
        ]):
            return 0.9
        
        # Medium confidence for copy-related keywords
        if any(word in request_lower for word in ["copy", "duplicate", "backup"]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file/directory copy."""
        try:
            # Get parameters from context
            source = context.get_state("source")
            destination = context.get_state("destination")
            
            # Try to extract from request if not in context
            if not source or not destination:
                extracted = self._extract_copy_parameters(context.user_request)
                source = source or extracted.get("source")
                destination = destination or extracted.get("destination")
            
            if not source:
                return ToolResult.error_result(
                    error="No source path specified",
                    tool_name=self.name
                )
            
            if not destination:
                return ToolResult.error_result(
                    error="No destination path specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            if await self._copy_with_mcp(source, destination, context):
                return ToolResult.success_result(
                    data={"source": source, "destination": destination, "method": "mcp"},
                    tool_name=self.name,
                    output=f"Copied {source} to {destination} (via MCP)"
                )
            
            # Fallback to local filesystem
            await self._copy_with_local(source, destination)
            return ToolResult.success_result(
                data={"source": source, "destination": destination, "method": "local"},
                tool_name=self.name,
                output=f"Copied {source} to {destination} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to copy: {str(e)}",
                tool_name=self.name
            )
    
    async def _copy_with_mcp(self, source: str, destination: str, context: ToolContext) -> bool:
        """Try to copy using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return False
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return False
            
            result = await mcp_fs.copy_file(source, destination)
            return result
            
        except Exception as e:
            self.logger.debug(f"MCP copy failed: {e}")
            return False
    
    async def _copy_with_local(self, source: str, destination: str) -> None:
        """Copy using local filesystem."""
        source_path = Path(source)
        dest_path = Path(destination)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        
        # Create parent directories if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if source_path.is_file():
            shutil.copy2(source_path, dest_path)
        elif source_path.is_dir():
            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
        else:
            raise ValueError(f"Unknown file type: {source}")
    
    def _extract_copy_parameters(self, request: str) -> dict:
        """Extract source and destination from request."""
        result = {"source": "", "destination": ""}
        
        # Look for copy patterns
        copy_patterns = [
            r'copy\s+([^\s]+)\s+to\s+([^\s]+)',
            r'copy\s+([^\s]+)\s+([^\s]+)',
            r'cp\s+([^\s]+)\s+([^\s]+)'
        ]
        
        for pattern in copy_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["source"] = matches[0][0]
                result["destination"] = matches[0][1]
                break
        
        return result