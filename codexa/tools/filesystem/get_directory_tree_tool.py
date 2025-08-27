"""
Get Directory Tree Tool for Codexa.
"""

from pathlib import Path
from typing import Set, Dict, Any
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class GetDirectoryTreeTool(Tool):
    """Tool for getting hierarchical directory structure with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "get_directory_tree"
    
    @property
    def description(self) -> str:
        return "Returns a hierarchical JSON representation of a directory structure"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"tree", "hierarchy", "structure", "navigation", "overview"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"directory_path"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit tree requests
        if any(phrase in request_lower for phrase in [
            "directory tree", "folder tree", "file tree", "tree view",
            "project structure", "directory structure", "show tree"
        ]):
            return 0.9
        
        # Medium confidence for structure/hierarchy requests
        if any(phrase in request_lower for phrase in [
            "structure", "hierarchy", "tree", "overview", "layout"
        ]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute directory tree generation."""
        try:
            # Get parameters from context
            directory_path = context.get_state("directory_path") or context.current_dir or "."
            depth = context.get_state("depth", 3)
            follow_symlinks = context.get_state("follow_symlinks", False)
            
            # Try to extract from request if needed
            extracted = self._extract_tree_parameters(context.user_request)
            if extracted.get("directory_path"):
                directory_path = extracted["directory_path"]
            if extracted.get("depth"):
                depth = extracted["depth"]
            
            # Try MCP filesystem first
            mcp_result = await self._get_tree_with_mcp(directory_path, depth, follow_symlinks, context)
            if mcp_result is not None:
                return ToolResult.success_result(
                    data={"tree": mcp_result, "path": directory_path, "depth": depth, "source": "mcp"},
                    tool_name=self.name,
                    output=f"Generated directory tree for: {directory_path} (via MCP)"
                )
            
            # Fallback to local filesystem
            local_result = await self._get_tree_with_local(directory_path, depth, follow_symlinks)
            return ToolResult.success_result(
                data={"tree": local_result, "path": directory_path, "depth": depth, "source": "local"},
                tool_name=self.name,
                output=f"Generated directory tree for: {directory_path} (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to generate directory tree: {str(e)}",
                tool_name=self.name
            )
    
    async def _get_tree_with_mcp(self, directory_path: str, depth: int, 
                               follow_symlinks: bool, context: ToolContext) -> Dict[str, Any]:
        """Try to get directory tree using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            tree = await mcp_fs.get_directory_tree(directory_path, depth, follow_symlinks)
            return tree
            
        except Exception as e:
            self.logger.debug(f"MCP tree failed: {e}")
            return None
    
    async def _get_tree_with_local(self, directory_path: str, depth: int, 
                                 follow_symlinks: bool) -> Dict[str, Any]:
        """Get directory tree using local filesystem."""
        path = Path(directory_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")
        
        def build_tree(current_path: Path, current_depth: int) -> Dict[str, Any]:
            """Recursively build directory tree."""
            tree = {
                "name": current_path.name,
                "path": str(current_path),
                "type": "directory",
                "size": 0,
                "children": []
            }
            
            if current_depth >= depth:
                return tree
            
            try:
                items = []
                total_size = 0
                
                for item in current_path.iterdir():
                    # Skip hidden files/dirs unless explicitly requested
                    if item.name.startswith('.'):
                        continue
                    
                    # Handle symlinks
                    if item.is_symlink() and not follow_symlinks:
                        continue
                    
                    try:
                        if item.is_dir():
                            child_tree = build_tree(item, current_depth + 1)
                            items.append(child_tree)
                            total_size += child_tree["size"]
                        else:
                            file_size = item.stat().st_size
                            file_info = {
                                "name": item.name,
                                "path": str(item),
                                "type": "file",
                                "size": file_size,
                                "extension": item.suffix.lower() if item.suffix else None,
                                "modified": item.stat().st_mtime
                            }
                            items.append(file_info)
                            total_size += file_size
                            
                    except (PermissionError, OSError) as e:
                        self.logger.debug(f"Skipping {item}: {e}")
                        continue
                
                # Sort items: directories first, then by name
                items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
                
                tree["children"] = items
                tree["size"] = total_size
                
            except PermissionError:
                self.logger.debug(f"Permission denied: {current_path}")
                tree["error"] = "Permission denied"
            
            return tree
        
        return build_tree(path, 0)
    
    def _extract_tree_parameters(self, request: str) -> Dict[str, Any]:
        """Extract tree parameters from request."""
        result = {"directory_path": "", "depth": None}
        
        # Look for directory path
        path_patterns = [
            r'tree\s+for\s+([^\s]+)',
            r'structure\s+of\s+([^\s]+)',
            r'tree\s+([^\s]+)',
            r'["\']([^"\']+)["\']'  # Quoted paths
        ]
        
        for pattern in path_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["directory_path"] = matches[0]
                break
        
        # Look for depth specification
        depth_patterns = [
            r'depth\s+(\d+)',
            r'level\s+(\d+)',
            r'(\d+)\s+levels?',
            r'max\s+(\d+)'
        ]
        
        for pattern in depth_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                try:
                    result["depth"] = int(matches[0])
                    break
                except ValueError:
                    continue
        
        return result