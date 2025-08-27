"""
Modify File Tool for Codexa.
"""

from pathlib import Path
from typing import Set, Dict, Any
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ModifyFileTool(Tool):
    """Tool for modifying file contents with find/replace operations."""
    
    @property
    def name(self) -> str:
        return "modify_file"
    
    @property
    def description(self) -> str:
        return "Update file by finding and replacing text"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"modify", "edit", "find_replace", "file_access", "content_modification"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path", "find_text"}
    
    @property
    def dependencies(self) -> Set[str]:
        return {"read_file"}  # Need to read file first
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit modify requests
        if any(phrase in request_lower for phrase in [
            "modify file", "edit file", "update file", "change file",
            "replace in file", "find and replace", "substitute in file"
        ]):
            return 0.9
        
        # Medium confidence for edit operations
        if any(phrase in request_lower for phrase in [
            "replace", "change", "update", "modify", "edit"
        ]) and any(word in request_lower for word in ["file", "text", "content"]):
            return 0.7
        
        # Medium confidence for find/replace patterns
        if "find" in request_lower and "replace" in request_lower:
            return 0.8
        
        # Low confidence for general modification keywords
        if any(word in request_lower for word in ["update", "modify", "edit", "change"]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file modification."""
        try:
            # Get parameters from context
            file_path = context.get_state("file_path")
            find_text = context.get_state("find_text")
            replace_text = context.get_state("replace_text", "")
            all_occurrences = context.get_state("all_occurrences", True)
            regex = context.get_state("regex", False)
            
            # Try to extract from request if not in context
            if not file_path or not find_text:
                extracted = self._extract_modify_parameters(context.user_request)
                file_path = file_path or extracted.get("file_path")
                find_text = find_text or extracted.get("find_text")
                replace_text = replace_text or extracted.get("replace_text", "")
            
            if not file_path:
                return ToolResult.error_result(
                    error="No file path specified",
                    tool_name=self.name
                )
            
            if not find_text:
                return ToolResult.error_result(
                    error="No find text specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            mcp_result = await self._modify_with_mcp(
                file_path, find_text, replace_text, all_occurrences, regex, context
            )
            if mcp_result:
                return ToolResult.success_result(
                    data=mcp_result,
                    tool_name=self.name,
                    files_modified=[file_path],
                    output=f"Modified file: {file_path} ({mcp_result.get('changes_made', 0)} changes via MCP)"
                )
            
            # Fallback to local filesystem
            local_result = await self._modify_with_local(
                file_path, find_text, replace_text, all_occurrences, regex
            )
            return ToolResult.success_result(
                data=local_result,
                tool_name=self.name,
                files_modified=[file_path],
                output=f"Modified file: {file_path} ({local_result.get('changes_made', 0)} changes local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to modify file: {str(e)}",
                tool_name=self.name
            )
    
    async def _modify_with_mcp(self, file_path: str, find_text: str, replace_text: str,
                             all_occurrences: bool, regex: bool, context: ToolContext) -> Dict[str, Any]:
        """Try to modify file using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            # Import MCP filesystem
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            result = await mcp_fs.modify_file(
                file_path, find_text, replace_text, all_occurrences, regex
            )
            return result
            
        except Exception as e:
            self.logger.debug(f"MCP modify failed: {e}")
            return None
    
    async def _modify_with_local(self, file_path: str, find_text: str, replace_text: str,
                               all_occurrences: bool, regex: bool) -> Dict[str, Any]:
        """Modify file using local filesystem."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read current content
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = path.read_text(encoding='utf-8', errors='ignore')
        
        original_content = content
        changes_made = 0
        
        # Perform replacement
        if regex:
            if all_occurrences:
                content, changes_made = re.subn(find_text, replace_text, content)
            else:
                content, changes_made = re.subn(find_text, replace_text, content, count=1)
        else:
            if all_occurrences:
                changes_made = content.count(find_text)
                content = content.replace(find_text, replace_text)
            else:
                if find_text in content:
                    content = content.replace(find_text, replace_text, 1)
                    changes_made = 1
        
        # Write back if changes were made
        if changes_made > 0:
            path.write_text(content, encoding='utf-8')
        
        return {
            "changes_made": changes_made,
            "original_length": len(original_content),
            "new_length": len(content),
            "file_path": str(path),
            "find_text": find_text,
            "replace_text": replace_text,
            "regex_used": regex,
            "all_occurrences": all_occurrences
        }
    
    def _extract_modify_parameters(self, request: str) -> Dict[str, str]:
        """Extract modification parameters from request string."""
        result = {"file_path": "", "find_text": "", "replace_text": ""}
        
        # Look for file paths with extensions
        file_pattern = r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        file_matches = re.findall(file_pattern, request)
        if file_matches:
            result["file_path"] = file_matches[0]
        
        # Look for find/replace patterns
        replace_patterns = [
            r'replace[:\s]+["\']([^"\']+)["\'][:\s]+with[:\s]+["\']([^"\']+)["\']',
            r'find[:\s]+["\']([^"\']+)["\'][:\s]+replace[:\s]+["\']([^"\']+)["\']',
            r'change[:\s]+["\']([^"\']+)["\'][:\s]+to[:\s]+["\']([^"\']+)["\']',
            r's/([^/]+)/([^/]*)/g?'  # sed-style replacement
        ]
        
        for pattern in replace_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["find_text"] = matches[0][0]
                result["replace_text"] = matches[0][1] if len(matches[0]) > 1 else ""
                break
        
        return result