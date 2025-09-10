"""
Serena-based file operations tools.
"""

from typing import Dict, Any, Set, List, Optional
import re

from ..base.tool_interface import ToolResult, ToolContext
from .base_serena_tool import BaseSerenaTool


class SerenaFileOperationsTool(BaseSerenaTool):
    """Tool for file operations using Serena's enhanced file handling."""
    
    @property
    def name(self) -> str:
        return "serena_file_operations"
    
    @property
    def description(self) -> str:
        return "Read, create, and modify files with semantic awareness and regex operations"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "file-read", "file-write", "file-create", "regex-replace",
            "semantic-file-ops", "smart-editing"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["read_file", "create_text_file", "replace_regex"]
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file operations."""
        try:
            request = context.user_request or ""
            request_lower = request.lower()
            
            # Determine operation type
            if any(word in request_lower for word in ["read", "show", "display", "view"]):
                return await self._read_file(context)
            elif any(word in request_lower for word in ["create", "write", "new file"]):
                return await self._create_file(context)
            elif any(word in request_lower for word in ["replace", "substitute", "regex", "pattern"]):
                return await self._replace_with_regex(context)
            else:
                # Default to read if file path detected
                if self._extract_file_path(context):
                    return await self._read_file(context)
                else:
                    return self._create_error_result("Could not determine file operation type")
                    
        except Exception as e:
            return self._create_error_result(f"File operation failed: {e}")
    
    async def _read_file(self, context: ToolContext) -> ToolResult:
        """Read file contents using Serena."""
        try:
            file_path = self._extract_file_path(context)
            if not file_path:
                return self._create_error_result("No file path provided for reading")
            
            # Read file content
            content = await self.call_serena_tool("read_file", {
                "file_path": file_path
            })
            
            if content is None:
                return self._create_error_result(f"Could not read file: {file_path}")
            
            # Format output
            lines = content.split('\n') if isinstance(content, str) else []
            line_count = len(lines)
            
            output = f"File: {file_path} ({line_count} lines)\n"
            output += "=" * 50 + "\n"
            output += content if isinstance(content, str) else str(content)
            
            return self._create_success_result(
                data={
                    "file_path": file_path,
                    "content": content,
                    "line_count": line_count,
                    "char_count": len(content) if isinstance(content, str) else 0
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"File read failed: {e}")
    
    async def _create_file(self, context: ToolContext) -> ToolResult:
        """Create or overwrite a file using Serena."""
        try:
            file_path = self._extract_file_path(context)
            if not file_path:
                return self._create_error_result("No file path provided for creation")
            
            content = self._extract_file_content(context)
            if content is None:
                return self._create_error_result("No content provided for file creation")
            
            # Create file
            success = await self.call_serena_tool("create_text_file", {
                "file_path": file_path,
                "content": content
            })
            
            if not success:
                return self._create_error_result(f"Failed to create file: {file_path}")
            
            lines = content.split('\n') if isinstance(content, str) else []
            
            return self._create_success_result(
                data={
                    "file_path": file_path,
                    "content": content,
                    "line_count": len(lines)
                },
                output=f"Created file: {file_path} ({len(lines)} lines)",
                files_created=[file_path]
            )
            
        except Exception as e:
            return self._create_error_result(f"File creation failed: {e}")
    
    async def _replace_with_regex(self, context: ToolContext) -> ToolResult:
        """Replace content in file using regex."""
        try:
            file_path = self._extract_file_path(context)
            if not file_path:
                return self._create_error_result("No file path provided for regex replacement")
            
            pattern, replacement = self._extract_regex_params(context)
            if not pattern:
                return self._create_error_result("No regex pattern provided")
            if replacement is None:
                return self._create_error_result("No replacement string provided")
            
            # Perform regex replacement
            success = await self.call_serena_tool("replace_regex", {
                "file_path": file_path,
                "pattern": pattern,
                "replacement": replacement
            })
            
            if not success:
                return self._create_error_result(f"Regex replacement failed in {file_path}")
            
            return self._create_success_result(
                data={
                    "file_path": file_path,
                    "pattern": pattern,
                    "replacement": replacement
                },
                output=f"Applied regex replacement in {file_path}\nPattern: {pattern}\nReplacement: {replacement}",
                files_modified=[file_path]
            )
            
        except Exception as e:
            return self._create_error_result(f"Regex replacement failed: {e}")
    
    def _extract_file_path(self, context: ToolContext) -> Optional[str]:
        """Extract file path from context or request."""
        request = context.user_request or ""
        
        # Look for file path patterns
        words = request.split()
        for word in words:
            # Check for file extensions
            if any(word.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php', '.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css']):
                return word
            # Check for path-like structure
            if '/' in word and '.' in word:
                return word
        
        # Check mentioned files in context
        mentioned_files = getattr(context, 'mentioned_files', [])
        if mentioned_files:
            return mentioned_files[0]
        
        # Check for patterns like "file X" or "in X"
        file_pattern = r'(?:file|in|path)\s+(\S+\.\w+)'
        match = re.search(file_pattern, request.lower())
        if match:
            return match.group(1)
        
        return None
    
    def _extract_file_content(self, context: ToolContext) -> Optional[str]:
        """Extract file content from request."""
        request = context.user_request or ""
        
        # Look for content in quotes
        content_patterns = [
            r'content\s*["\']([^"\']*)["\']',
            r'with\s*["\']([^"\']*)["\']',
            r'["\']([^"\']{10,})["\']'  # Long quoted strings
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, request, re.DOTALL)
            if match:
                return match.group(1)
        
        # Look for code blocks
        code_block_pattern = r'```(?:\w+)?\n(.*?)\n```'
        match = re.search(code_block_pattern, request, re.DOTALL)
        if match:
            return match.group(1)
        
        # Check if content is provided after "with" or "containing"
        content_keywords = ["with", "containing", "content"]
        for keyword in content_keywords:
            if keyword in request.lower():
                parts = request.lower().split(keyword, 1)
                if len(parts) > 1:
                    content = parts[1].strip()
                    # Remove common prefixes
                    content = re.sub(r'^(the\s+)?(content\s+)?', '', content)
                    if content:
                        return content
        
        return None
    
    def _extract_regex_params(self, context: ToolContext) -> tuple:
        """Extract regex pattern and replacement from request."""
        request = context.user_request or ""
        
        # Look for explicit pattern/replacement format
        explicit_patterns = [
            r'pattern\s*["\']([^"\']*)["\'].*?replacement\s*["\']([^"\']*)["\']',
            r'replace\s*["\']([^"\']*)["\'].*?with\s*["\']([^"\']*)["\']',
            r's/([^/]*)/([^/]*)/g?'  # sed-style
        ]
        
        for pattern in explicit_patterns:
            match = re.search(pattern, request, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1), match.group(2)
        
        # Look for simpler "replace X with Y" format
        replace_pattern = r'replace\s+(.+?)\s+with\s+(.+?)(?:\s|$)'
        match = re.search(replace_pattern, request, re.IGNORECASE)
        if match:
            pattern = match.group(1).strip('\'"')
            replacement = match.group(2).strip('\'"')
            return pattern, replacement
        
        return None, None


class PatternSearchTool(BaseSerenaTool):
    """Tool for searching patterns in project files using Serena."""
    
    @property
    def name(self) -> str:
        return "serena_pattern_search"
    
    @property
    def description(self) -> str:
        return "Search for text patterns across project files with filtering options"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "pattern-search", "text-search", "grep", "find-in-files",
            "project-search", "regex-search"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["search_for_pattern"]
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute pattern search."""
        try:
            # Extract search pattern
            pattern = self._extract_search_pattern(context)
            if not pattern:
                return self._create_error_result("No search pattern provided")
            
            # Extract file filters
            include_files, exclude_files = self._extract_file_filters(context)
            
            # Build search parameters
            search_params = {"pattern": pattern}
            if include_files:
                search_params["include_files"] = include_files
            if exclude_files:
                search_params["exclude_files"] = exclude_files
            
            # Search for pattern
            results = await self.call_serena_tool("search_for_pattern", search_params)
            
            if not results:
                return self._create_success_result(
                    data={
                        "results": [],
                        "pattern": pattern,
                        "include_files": include_files,
                        "exclude_files": exclude_files
                    },
                    output=f"No matches found for pattern: {pattern}"
                )
            
            # Format results
            output = self._format_search_results(results, pattern)
            
            return self._create_success_result(
                data={
                    "results": results,
                    "pattern": pattern,
                    "include_files": include_files,
                    "exclude_files": exclude_files,
                    "match_count": len(results) if isinstance(results, list) else 1
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Pattern search failed: {e}")
    
    def _extract_search_pattern(self, context: ToolContext) -> Optional[str]:
        """Extract search pattern from request."""
        request = context.user_request or ""
        
        # Look for quoted patterns first
        quoted_patterns = re.findall(r'["\']([^"\']+)["\']', request)
        if quoted_patterns:
            return quoted_patterns[0]
        
        # Look for "search for X", "find X", "grep X" patterns
        search_patterns = [
            r'search\s+for\s+(.+?)(?:\s+in|\s+from|$)',
            r'find\s+(.+?)(?:\s+in|\s+from|$)',
            r'grep\s+(.+?)(?:\s+in|\s+from|$)',
            r'look\s+for\s+(.+?)(?:\s+in|\s+from|$)',
            r'pattern\s+(.+?)(?:\s+in|\s+from|$)'
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Default: use last meaningful word
        words = [word for word in request.split() if len(word) > 2]
        if words:
            return words[-1]
        
        return None
    
    def _extract_file_filters(self, context: ToolContext) -> tuple:
        """Extract include and exclude file filters from request."""
        request = context.user_request or ""
        
        include_files = []
        exclude_files = []
        
        # Look for include patterns
        include_patterns = [
            r'in\s+(.+?\.(?:py|js|ts|java|cpp|c|h|go|rs|rb|php))',
            r'include\s+(.+?)(?:\s|$)',
            r'only\s+(.+?\.(?:py|js|ts|java|cpp|c|h|go|rs|rb|php))'
        ]
        
        for pattern in include_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            include_files.extend(matches)
        
        # Look for exclude patterns
        exclude_patterns = [
            r'exclude\s+(.+?)(?:\s|$)',
            r'ignore\s+(.+?)(?:\s|$)',
            r'not\s+(.+?\.(?:py|js|ts|java|cpp|c|h|go|rs|rb|php))'
        ]
        
        for pattern in exclude_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            exclude_files.extend(matches)
        
        # Auto-detect file types if none specified
        if not include_files and not exclude_files:
            # Default to common code file types
            if any(word in request.lower() for word in ["code", "function", "class", "method"]):
                include_files = ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.c", "*.h", "*.go"]
        
        return include_files or None, exclude_files or None
    
    def _format_search_results(self, results: Any, pattern: str) -> str:
        """Format pattern search results."""
        output = [f"Search results for pattern: {pattern}"]
        
        if isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    file_path = result.get('file', 'Unknown file')
                    line_number = result.get('line', 'N/A')
                    match_text = result.get('match', result.get('text', ''))
                    
                    output.append(f"\n{file_path}:{line_number}")
                    output.append(f"  {match_text.strip()}")
                else:
                    output.append(f"  {result}")
        elif isinstance(results, dict):
            # Single result
            file_path = results.get('file', 'Unknown file')
            line_number = results.get('line', 'N/A')
            match_text = results.get('match', results.get('text', ''))
            
            output.append(f"\n{file_path}:{line_number}")
            output.append(f"  {match_text.strip()}")
        
        count = len(results) if isinstance(results, list) else 1
        output.append(f"\nFound {count} match(es)")
        return "\n".join(output)