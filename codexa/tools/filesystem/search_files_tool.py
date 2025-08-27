"""
Search Files Tool for Codexa.
"""

from pathlib import Path
from typing import Set, List, Dict, Any
import re
import fnmatch

from ..base.tool_interface import Tool, ToolResult, ToolContext


class SearchFilesTool(Tool):
    """Tool for searching files by name/pattern with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "search_files"
    
    @property
    def description(self) -> str:
        return "Recursively search for files and directories matching a pattern"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"search", "find", "pattern_matching", "file_discovery"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"pattern"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit search requests
        if any(phrase in request_lower for phrase in [
            "search files", "find files", "search for files", "locate files",
            "find file", "search file", "look for files", "files matching"
        ]):
            return 0.9
        
        # Medium confidence for search patterns
        if any(phrase in request_lower for phrase in [
            "*.py", "*.js", "*.txt", "*.json", "*.",  # File patterns
            "find", "search", "locate", "grep", "pattern"
        ]):
            return 0.7
        
        # Low confidence for general search keywords
        if any(word in request_lower for word in ["find", "search", "locate"]):
            return 0.4
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file search."""
        try:
            # Get parameters from context
            pattern = context.get_state("pattern")
            search_path = context.get_state("search_path") or context.current_dir or "."
            
            # Try to extract from request if not in context
            if not pattern:
                extracted = self._extract_search_parameters(context.user_request)
                pattern = extracted.get("pattern")
                search_path = extracted.get("path") or search_path
            
            if not pattern:
                return ToolResult.error_result(
                    error="No search pattern specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            mcp_result = await self._search_with_mcp(search_path, pattern, context)
            if mcp_result is not None:
                return ToolResult.success_result(
                    data={"matches": mcp_result, "pattern": pattern, "path": search_path, "source": "mcp"},
                    tool_name=self.name,
                    output=f"Found {len(mcp_result)} files matching '{pattern}' (via MCP)"
                )
            
            # Fallback to local filesystem
            local_result = await self._search_with_local(search_path, pattern)
            return ToolResult.success_result(
                data={"matches": local_result, "pattern": pattern, "path": search_path, "source": "local"},
                tool_name=self.name,
                output=f"Found {len(local_result)} files matching '{pattern}' (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to search files: {str(e)}",
                tool_name=self.name
            )
    
    async def _search_with_mcp(self, search_path: str, pattern: str, context: ToolContext) -> List[Dict[str, Any]]:
        """Try to search files using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            # Import MCP filesystem
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            matches = await mcp_fs.search_files(search_path, pattern)
            return matches
            
        except Exception as e:
            self.logger.debug(f"MCP search failed: {e}")
            return None
    
    async def _search_with_local(self, search_path: str, pattern: str) -> List[Dict[str, Any]]:
        """Search files using local filesystem."""
        path = Path(search_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Search path not found: {search_path}")
        
        matches = []
        
        def search_recursive(current_path: Path, depth: int = 0):
            """Recursively search for files matching pattern."""
            if depth > 10:  # Prevent infinite recursion
                return
            
            try:
                for item in current_path.iterdir():
                    # Skip hidden directories and files by default
                    if item.name.startswith('.') and not pattern.startswith('.'):
                        continue
                    
                    # Check if name matches pattern
                    if fnmatch.fnmatch(item.name.lower(), pattern.lower()):
                        match = {
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": item.stat().st_size if item.is_file() else 0,
                            "modified": item.stat().st_mtime,
                            "relative_path": str(item.relative_to(path)),
                            "depth": depth,
                            "extension": item.suffix.lower() if item.is_file() else None
                        }
                        matches.append(match)
                    
                    # Recurse into subdirectories
                    if item.is_dir() and not item.is_symlink():
                        search_recursive(item, depth + 1)
                        
            except PermissionError:
                self.logger.debug(f"Permission denied: {current_path}")
            except Exception as e:
                self.logger.debug(f"Error searching {current_path}: {e}")
        
        # Start search
        if path.is_dir():
            search_recursive(path)
        else:
            # Single file check
            if fnmatch.fnmatch(path.name.lower(), pattern.lower()):
                matches.append({
                    "name": path.name,
                    "path": str(path),
                    "type": "file",
                    "size": path.stat().st_size,
                    "modified": path.stat().st_mtime,
                    "relative_path": path.name,
                    "depth": 0,
                    "extension": path.suffix.lower()
                })
        
        # Sort by relevance (exact matches first, then by depth, then by name)
        matches.sort(key=lambda x: (
            x["name"].lower() != pattern.lower(),  # Exact matches first
            x["depth"],  # Shallower first
            x["name"].lower()  # Alphabetical
        ))
        
        return matches
    
    def _extract_search_parameters(self, request: str) -> Dict[str, str]:
        """Extract search parameters from request string."""
        result = {"pattern": "", "path": ""}
        
        # Look for file patterns
        pattern_patterns = [
            r'search for\s+([^\s]+)',
            r'find\s+([^\s]+)',
            r'files?\s+matching\s+([^\s]+)',
            r'pattern\s+([^\s]+)',
            r'(\*\.[a-zA-Z0-9]+)',  # File extension patterns
            r'["\']([^"\']+)["\']'  # Quoted patterns
        ]
        
        for pattern in pattern_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["pattern"] = matches[0]
                break
        
        # Look for path specifications
        path_patterns = [
            r'in\s+([a-zA-Z0-9_/.-]+)',
            r'directory\s+([a-zA-Z0-9_/.-]+)',
            r'folder\s+([a-zA-Z0-9_/.-]+)',
            r'under\s+([a-zA-Z0-9_/.-]+)'
        ]
        
        for pattern in path_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["path"] = matches[0]
                break
        
        return result