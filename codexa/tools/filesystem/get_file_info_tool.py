"""
Get File Info Tool for Codexa.
"""

from pathlib import Path
from typing import Set, Dict, Any
import re
import mimetypes
from datetime import datetime

from ..base.tool_interface import Tool, ToolResult, ToolContext


class GetFileInfoTool(Tool):
    """Tool for retrieving detailed file/directory metadata with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "get_file_info"
    
    @property
    def description(self) -> str:
        return "Retrieve detailed metadata about a file or directory"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"info", "metadata", "stats", "properties"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit info requests
        if any(phrase in request_lower for phrase in [
            "file info", "file information", "file details", "file metadata",
            "file stats", "file properties", "info about", "details about"
        ]):
            return 0.9
        
        # Medium confidence for info-related keywords
        if any(phrase in request_lower for phrase in [
            "info", "information", "details", "metadata", "stats", "properties"
        ]) and any(word in request_lower for word in ["file", "directory", "path"]):
            return 0.7
        
        # Low confidence for general inquiry keywords
        if any(word in request_lower for word in ["info", "details", "stats"]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file info retrieval."""
        try:
            # Get file path from context
            file_path = context.get_state("file_path")
            
            # Try to extract from request if not in context
            if not file_path:
                file_path = self._extract_file_path(context.user_request)
            
            if not file_path:
                return ToolResult.error_result(
                    error="No file path specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            mcp_result = await self._get_info_with_mcp(file_path, context)
            if mcp_result is not None:
                return ToolResult.success_result(
                    data=mcp_result,
                    tool_name=self.name,
                    output=f"Retrieved file info: {file_path} (via MCP)"
                )
            
            # Fallback to local filesystem
            local_result = await self._get_info_with_local(file_path)
            return ToolResult.success_result(
                data=local_result,
                tool_name=self.name,
                output=f"Retrieved file info: {file_path} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to get file info: {str(e)}",
                tool_name=self.name
            )
    
    async def _get_info_with_mcp(self, file_path: str, context: ToolContext) -> Dict[str, Any]:
        """Try to get file info using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            info = await mcp_fs.get_file_info(file_path)
            return info
            
        except Exception as e:
            self.logger.debug(f"MCP file info failed: {e}")
            return None
    
    async def _get_info_with_local(self, file_path: str) -> Dict[str, Any]:
        """Get file info using local filesystem."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {file_path}")
        
        stat = path.stat()
        
        # Basic file information
        info = {
            "name": path.name,
            "path": str(path.absolute()),
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "size_human": self._format_size(stat.st_size),
            "created": stat.st_ctime,
            "created_iso": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": stat.st_mtime,
            "modified_iso": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": stat.st_atime,
            "accessed_iso": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "permissions_full": oct(stat.st_mode),
            "owner_read": bool(stat.st_mode & 0o400),
            "owner_write": bool(stat.st_mode & 0o200),
            "owner_execute": bool(stat.st_mode & 0o100),
            "is_hidden": path.name.startswith('.'),
            "is_symlink": path.is_symlink()
        }
        
        # File-specific information
        if path.is_file():
            info.update({
                "extension": path.suffix.lower() if path.suffix else None,
                "stem": path.stem,
                "mime_type": mimetypes.guess_type(str(path))[0],
                "encoding": mimetypes.guess_type(str(path))[1]
            })
            
            # Try to detect if it's a text file
            try:
                with open(path, 'rb') as f:
                    sample = f.read(8192)
                    is_text = self._is_text_file(sample)
                    info["is_text"] = is_text
                    
                    if is_text:
                        # Count lines for text files
                        f.seek(0)
                        try:
                            content = f.read().decode('utf-8')
                            info["line_count"] = content.count('\n') + 1
                            info["character_count"] = len(content)
                            info["word_count"] = len(content.split())
                        except UnicodeDecodeError:
                            pass
                            
            except (PermissionError, OSError):
                pass
        
        # Directory-specific information
        elif path.is_dir():
            try:
                children = list(path.iterdir())
                files = [p for p in children if p.is_file()]
                dirs = [p for p in children if p.is_dir()]
                
                info.update({
                    "total_items": len(children),
                    "file_count": len(files),
                    "directory_count": len(dirs),
                    "hidden_items": len([p for p in children if p.name.startswith('.')]),
                    "largest_file": max(files, key=lambda x: x.stat().st_size) if files else None,
                    "total_size": sum(f.stat().st_size for f in files if f.is_file())
                })
                
                if info["largest_file"]:
                    info["largest_file"] = str(info["largest_file"])
                    
                info["total_size_human"] = self._format_size(info["total_size"])
                
            except PermissionError:
                info["directory_error"] = "Permission denied"
        
        # Symlink information
        if path.is_symlink():
            try:
                info["symlink_target"] = str(path.readlink())
                info["symlink_broken"] = not path.exists()
            except OSError:
                info["symlink_error"] = "Cannot read symlink target"
        
        return info
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def _is_text_file(self, sample: bytes) -> bool:
        """Check if file appears to be text based on sample."""
        # Check for null bytes (binary files usually contain them)
        if b'\x00' in sample:
            return False
        
        # Check for high percentage of printable characters
        try:
            sample.decode('utf-8')
            return True
        except UnicodeDecodeError:
            pass
        
        # Try other encodings
        for encoding in ['latin-1', 'cp1252']:
            try:
                decoded = sample.decode(encoding)
                printable_chars = sum(1 for c in decoded if c.isprintable() or c.isspace())
                ratio = printable_chars / len(decoded)
                return ratio > 0.7  # 70% printable characters
            except UnicodeDecodeError:
                continue
        
        return False
    
    def _extract_file_path(self, request: str) -> str:
        """Extract file path from request."""
        # Look for file path patterns
        patterns = [
            r'info\s+(?:about\s+|for\s+)?([^\s]+)',
            r'details\s+(?:about\s+|for\s+)?([^\s]+)',
            r'stats\s+(?:about\s+|for\s+)?([^\s]+)',
            r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)',  # Files with extensions
            r'["\']([^"\']+)["\']'  # Quoted paths
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return ""