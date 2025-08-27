"""
Read Multiple Files Tool for Codexa.
"""

from pathlib import Path
from typing import Set, List, Dict
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ReadMultipleFilesTool(Tool):
    """Tool for reading multiple files efficiently with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "read_multiple_files"
    
    @property
    def description(self) -> str:
        return "Read multiple files in a single operation for efficiency"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"read", "batch", "multi_file", "content_retrieval"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_paths"}
    
    @property
    def dependencies(self) -> Set[str]:
        return {"read_file"}  # Can fallback to single file reads
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit multiple file requests
        if any(phrase in request_lower for phrase in [
            "read multiple files", "read all files", "read these files",
            "read several files", "batch read", "read files"
        ]):
            return 0.9
        
        # Medium confidence if multiple file paths detected
        file_count = len(re.findall(r'[a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+', request))
        if file_count > 1:
            return 0.7
        
        # Low confidence for general read requests
        if "read" in request_lower and "files" in request_lower:
            return 0.4
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute multiple file reading."""
        try:
            # Get file paths from context
            file_paths = context.get_state("file_paths", [])
            
            # Try to extract from request if not in context
            if not file_paths:
                file_paths = self._extract_file_paths(context.user_request)
            
            if not file_paths:
                return ToolResult.error_result(
                    error="No file paths specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            mcp_result = await self._read_with_mcp(file_paths, context)
            if mcp_result is not None:
                return ToolResult.success_result(
                    data={"files": mcp_result, "file_count": len(mcp_result), "source": "mcp"},
                    tool_name=self.name,
                    output=f"Read {len(mcp_result)} files (via MCP)"
                )
            
            # Fallback to local filesystem
            local_result = await self._read_with_local(file_paths)
            return ToolResult.success_result(
                data={"files": local_result, "file_count": len(local_result), "source": "local"},
                tool_name=self.name,
                output=f"Read {len(local_result)} files (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to read multiple files: {str(e)}",
                tool_name=self.name
            )
    
    async def _read_with_mcp(self, file_paths: List[str], context: ToolContext) -> Dict[str, str]:
        """Try to read files using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            # Convert to Path objects for MCP
            path_objects = [Path(p) for p in file_paths]
            files_dict = await mcp_fs.read_multiple_files(path_objects)
            return files_dict
            
        except Exception as e:
            self.logger.debug(f"MCP multiple read failed: {e}")
            return None
    
    async def _read_with_local(self, file_paths: List[str]) -> Dict[str, str]:
        """Read multiple files using local filesystem."""
        files_dict = {}
        
        for file_path in file_paths:
            try:
                path = Path(file_path)
                
                if not path.exists():
                    files_dict[file_path] = f"ERROR: File not found"
                    continue
                
                if not path.is_file():
                    files_dict[file_path] = f"ERROR: Path is not a file"
                    continue
                
                # Read file content
                try:
                    content = path.read_text(encoding='utf-8')
                    files_dict[file_path] = content
                except UnicodeDecodeError:
                    # Try other encodings
                    for encoding in ['latin-1', 'cp1252', 'ascii']:
                        try:
                            content = path.read_text(encoding=encoding)
                            files_dict[file_path] = content
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        # If all encodings fail, read with errors='ignore'
                        content = path.read_text(encoding='utf-8', errors='ignore')
                        files_dict[file_path] = content
                        
            except Exception as e:
                files_dict[file_path] = f"ERROR: {str(e)}"
        
        return files_dict
    
    def _extract_file_paths(self, request: str) -> List[str]:
        """Extract multiple file paths from request."""
        # Look for file paths with extensions
        file_pattern = r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        file_paths = re.findall(file_pattern, request)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in file_paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)
        
        return unique_paths