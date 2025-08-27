"""
Search Within Files Tool for Codexa.
"""

from pathlib import Path
from typing import Set, List, Dict, Any, Optional
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class SearchWithinFilesTool(Tool):
    """Tool for searching text within file contents with MCP fallback."""
    
    @property
    def name(self) -> str:
        return "search_within_files"
    
    @property
    def description(self) -> str:
        return "Search for text within file contents across directory trees"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"search", "grep", "content_search", "text_search"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"search_text"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit content search requests
        if any(phrase in request_lower for phrase in [
            "search within files", "search in files", "grep", "find text",
            "search content", "find in files", "content search", "text search"
        ]):
            return 0.9
        
        # Medium confidence for search with content indicators
        if any(phrase in request_lower for phrase in [
            "search for", "find", "locate"
        ]) and any(phrase in request_lower for phrase in [
            "text", "content", "string", "word", "phrase"
        ]):
            return 0.7
        
        # Low confidence for general search terms
        if any(word in request_lower for word in ["search", "find", "grep"]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute content search within files."""
        try:
            # Get parameters from context
            search_text = context.get_state("search_text")
            search_path = context.get_state("search_path") or context.current_dir or "."
            depth = context.get_state("depth")
            max_results = context.get_state("max_results", 1000)
            case_sensitive = context.get_state("case_sensitive", False)
            regex = context.get_state("regex", False)
            
            # Try to extract from request if not in context
            if not search_text:
                extracted = self._extract_search_parameters(context.user_request)
                search_text = extracted.get("search_text")
                search_path = extracted.get("search_path") or search_path
                case_sensitive = extracted.get("case_sensitive", case_sensitive)
                regex = extracted.get("regex", regex)
            
            if not search_text:
                return ToolResult.error_result(
                    error="No search text specified",
                    tool_name=self.name
                )
            
            # Try MCP filesystem first
            mcp_result = await self._search_with_mcp(
                search_path, search_text, depth, max_results, context
            )
            if mcp_result is not None:
                return ToolResult.success_result(
                    data={
                        "matches": mcp_result,
                        "search_text": search_text,
                        "path": search_path,
                        "source": "mcp"
                    },
                    tool_name=self.name,
                    output=f"Found {len(mcp_result)} matches for '{search_text}' (via MCP)"
                )
            
            # Fallback to local filesystem
            local_result = await self._search_with_local(
                search_path, search_text, depth, max_results, case_sensitive, regex
            )
            return ToolResult.success_result(
                data={
                    "matches": local_result,
                    "search_text": search_text,
                    "path": search_path,
                    "source": "local"
                },
                tool_name=self.name,
                output=f"Found {len(local_result)} matches for '{search_text}' (local)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to search within files: {str(e)}",
                tool_name=self.name
            )
    
    async def _search_with_mcp(self, search_path: str, search_text: str, 
                             depth: Optional[int], max_results: int, 
                             context: ToolContext) -> List[Dict[str, Any]]:
        """Try to search within files using MCP filesystem."""
        try:
            if not context.mcp_service or not context.mcp_service.is_running:
                return None
            
            from ...filesystem.mcp_filesystem import MCPFileSystem
            mcp_fs = MCPFileSystem(context.mcp_service)
            
            if not mcp_fs.is_server_available():
                return None
            
            matches = await mcp_fs.search_within_files(
                search_path, search_text, depth, max_results
            )
            return matches
            
        except Exception as e:
            self.logger.debug(f"MCP content search failed: {e}")
            return None
    
    async def _search_with_local(self, search_path: str, search_text: str,
                               depth: Optional[int], max_results: int,
                               case_sensitive: bool, regex: bool) -> List[Dict[str, Any]]:
        """Search within files using local filesystem."""
        path = Path(search_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Search path not found: {search_path}")
        
        matches = []
        results_count = 0
        
        # Compile search pattern
        if regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(search_text, flags)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        else:
            # Escape special regex characters for literal search
            escaped_text = re.escape(search_text)
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(escaped_text, flags)
        
        def search_file(file_path: Path) -> List[Dict[str, Any]]:
            """Search within a single file."""
            file_matches = []
            
            # Skip binary files and very large files
            try:
                if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
                    return file_matches
            except OSError:
                return file_matches
            
            try:
                # Try different encodings
                content = None
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    return file_matches
                
                # Search for matches
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    for match in pattern.finditer(line):
                        file_matches.append({
                            "file": str(file_path),
                            "line_number": line_num,
                            "line_content": line.strip(),
                            "match_start": match.start(),
                            "match_end": match.end(),
                            "matched_text": match.group(),
                            "file_size": file_path.stat().st_size,
                            "file_modified": file_path.stat().st_mtime,
                            "relative_path": str(file_path.relative_to(path)) if file_path.is_relative_to(path) else str(file_path)
                        })
                        
                        # Add context lines if available
                        context_lines = []
                        for ctx_offset in [-2, -1, 1, 2]:
                            ctx_line_num = line_num + ctx_offset
                            if 0 < ctx_line_num <= len(lines) and ctx_line_num != line_num:
                                context_lines.append({
                                    "line_number": ctx_line_num,
                                    "content": lines[ctx_line_num - 1].strip()
                                })
                        
                        file_matches[-1]["context"] = context_lines
                
            except (PermissionError, OSError, UnicodeDecodeError) as e:
                self.logger.debug(f"Error reading {file_path}: {e}")
            
            return file_matches
        
        def search_recursive(current_path: Path, current_depth: int = 0):
            """Recursively search files."""
            nonlocal results_count
            
            if results_count >= max_results:
                return
            
            if depth is not None and current_depth > depth:
                return
            
            try:
                for item in current_path.iterdir():
                    if results_count >= max_results:
                        break
                    
                    # Skip hidden files and directories
                    if item.name.startswith('.'):
                        continue
                    
                    if item.is_file():
                        # Only search text-like files
                        if self._is_searchable_file(item):
                            file_matches = search_file(item)
                            matches.extend(file_matches)
                            results_count += len(file_matches)
                    
                    elif item.is_dir() and not item.is_symlink():
                        search_recursive(item, current_depth + 1)
                        
            except PermissionError:
                self.logger.debug(f"Permission denied: {current_path}")
            except Exception as e:
                self.logger.debug(f"Error searching {current_path}: {e}")
        
        # Start search
        if path.is_file():
            if self._is_searchable_file(path):
                matches = search_file(path)
        else:
            search_recursive(path)
        
        # Sort matches by relevance (file name, then line number)
        matches.sort(key=lambda x: (x["file"], x["line_number"]))
        
        return matches[:max_results]
    
    def _is_searchable_file(self, file_path: Path) -> bool:
        """Check if file is suitable for text search."""
        # Check file extension
        text_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css',
            '.scss', '.sass', '.json', '.yaml', '.yml', '.xml', '.csv', '.sql',
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.ini',
            '.cfg', '.conf', '.config', '.properties', '.env', '.gitignore',
            '.dockerfile', '.makefile', '.readme', '.rst', '.tex', '.log'
        }
        
        if file_path.suffix.lower() in text_extensions:
            return True
        
        # Check files without extension that are commonly text
        if not file_path.suffix:
            text_names = {
                'readme', 'license', 'changelog', 'makefile', 'dockerfile',
                'gemfile', 'rakefile', 'vagrantfile', 'procfile'
            }
            if file_path.name.lower() in text_names:
                return True
        
        # Quick binary check for other files
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(8192)
                # If it contains null bytes, likely binary
                return b'\x00' not in sample
        except (OSError, PermissionError):
            return False
    
    def _extract_search_parameters(self, request: str) -> Dict[str, Any]:
        """Extract search parameters from request."""
        result = {
            "search_text": "",
            "search_path": "",
            "case_sensitive": False,
            "regex": False
        }
        
        # Check for regex flag
        if any(word in request.lower() for word in ["regex", "regexp", "pattern"]):
            result["regex"] = True
        
        # Check for case sensitivity
        if any(phrase in request.lower() for phrase in ["case sensitive", "case-sensitive"]):
            result["case_sensitive"] = True
        
        # Look for search text patterns
        text_patterns = [
            r'search for\s+["\']([^"\']+)["\']',
            r'find\s+["\']([^"\']+)["\']',
            r'grep\s+["\']([^"\']+)["\']',
            r'text\s+["\']([^"\']+)["\']',
            r'["\']([^"\']{3,})["\']'  # Any quoted string with 3+ chars
        ]
        
        for pattern in text_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["search_text"] = matches[0]
                break
        
        # Look for path specifications
        path_patterns = [
            r'in\s+([a-zA-Z0-9_/.-]+)',
            r'within\s+([a-zA-Z0-9_/.-]+)',
            r'under\s+([a-zA-Z0-9_/.-]+)'
        ]
        
        for pattern in path_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["search_path"] = matches[0]
                break
        
        return result