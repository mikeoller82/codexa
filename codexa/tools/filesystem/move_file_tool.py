"""
Move File Tool for Codexa.
"""

from pathlib import Path
from typing import Set
import shutil
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MoveFileTool(Tool):
    """Tool for moving/renaming files and directories with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "move_file"
    
    @property
    def description(self) -> str:
        return "Move or rename files and directories"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"move", "rename", "relocate", "file_management"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"source", "destination"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit move/rename requests
        if any(phrase in request_lower for phrase in [
            "move file", "move directory", "rename file", "rename directory",
            "move to", "rename to", "mv ", "relocate"
        ]):
            return 0.9
        
        # Medium confidence for move-related keywords
        if any(word in request_lower for word in ["move", "rename", "relocate"]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file/directory move."""
        try:
            # Get parameters from context
            source = context.get_state("source")
            destination = context.get_state("destination")
            
            # Try to extract from request if not in context
            if not source or not destination:
                extracted = self._extract_move_parameters(context.user_request)
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
            if await self._move_with_mcp(source, destination, context):
                return ToolResult.success_result(
                    data={"source": source, "destination": destination, "method": "mcp"},
                    tool_name=self.name,
                    files_modified=[destination],
                    output=f"Moved {source} to {destination} (via MCP)"
                )
            
            # Fallback to local filesystem
            await self._move_with_local(source, destination)
            return ToolResult.success_result(
                data={"source": source, "destination": destination, "method": "local"},
                tool_name=self.name,
                files_modified=[destination],
                output=f"Moved {source} to {destination} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to move: {str(e)}",
                tool_name=self.name
            )
    
    async def _move_with_mcp(self, source: str, destination: str, context: ToolContext) -> bool:
        """Try to move using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return False
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return False
            
            result = await mcp_fs.move_file(source, destination)
            return result
            
        except Exception as e:
            self.logger.debug(f"MCP move failed: {e}")
            return False
    
    async def _move_with_local(self, source: str, destination: str) -> None:
        """Move using local filesystem."""
        source_path = Path(source)
        dest_path = Path(destination)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        
        # Create parent directories if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use shutil.move for cross-platform compatibility
        shutil.move(str(source_path), str(dest_path))
    
    def _extract_move_parameters(self, request: str) -> dict:
        """Extract source and destination from request."""
        result = {"source": "", "destination": ""}
        
        # Look for move/rename patterns
        move_patterns = [
            r'move\s+([^\s]+)\s+to\s+([^\s]+)',
            r'move\s+([^\s]+)\s+([^\s]+)',
            r'rename\s+([^\s]+)\s+to\s+([^\s]+)',
            r'rename\s+([^\s]+)\s+([^\s]+)',
            r'mv\s+([^\s]+)\s+([^\s]+)'
        ]
        
        for pattern in move_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["source"] = matches[0][0]
                result["destination"] = matches[0][1]
                break
        
        return result