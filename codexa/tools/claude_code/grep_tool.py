"""
Grep tool - A powerful search tool built on ripgrep for content searching.
"""

import os
import subprocess
import re
from pathlib import Path
from typing import Set, List, Dict, Any, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class GrepTool(Tool):
    """A powerful search tool built on ripgrep for content searching."""
    
    # Claude Code schema compatibility
    CLAUDE_CODE_SCHEMA = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The regular expression pattern to search for in file contents"
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in"
            },
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count"],
                "description": "Output mode"
            },
            "-i": {
                "type": "boolean",
                "description": "Case insensitive search"
            }
        },
        "required": ["pattern"],
        "additionalProperties": False
    }
    
    @property
    def name(self) -> str:
        return "Grep"
    
    @property
    def description(self) -> str:
        return "A powerful search tool built on ripgrep for content searching with regex support"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"pattern"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit search terms
        if any(phrase in request_lower for phrase in [
            "search for", "find text", "grep", "search content", "find in files"
        ]):
            return 0.9
        
        # Medium confidence for search-related keywords
        if any(phrase in request_lower for phrase in [
            "search", "find", "locate", "contains", "match"
        ]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the Grep tool."""
        try:
            # Extract parameters
            pattern = context.get_state("pattern")
            if not pattern:
                return ToolResult.error_result(
                    error="Missing required parameter: pattern",
                    tool_name=self.name
                )
            
            # Optional parameters
            path = context.get_state("path") or context.current_dir or context.current_path or os.getcwd()
            glob_pattern = context.get_state("glob")
            output_mode = context.get_state("output_mode", "files_with_matches")
            case_insensitive = context.get_state("-i", False)
            before_context = context.get_state("-B")
            after_context = context.get_state("-A") 
            context_lines = context.get_state("-C")
            show_line_numbers = context.get_state("-n", False)
            file_type = context.get_state("type")
            head_limit = context.get_state("head_limit")
            multiline = context.get_state("multiline", False)
            
            # Build ripgrep command
            rg_cmd = ["rg"]
            
            # Output mode settings
            if output_mode == "files_with_matches":
                rg_cmd.append("--files-with-matches")
            elif output_mode == "count":
                rg_cmd.append("--count")
            # content mode is default, no flag needed
            
            # Context options (only for content mode)
            if output_mode == "content":
                if context_lines is not None:
                    rg_cmd.extend(["-C", str(context_lines)])
                elif before_context is not None:
                    rg_cmd.extend(["-B", str(before_context)])
                elif after_context is not None:
                    rg_cmd.extend(["-A", str(after_context)])
                
                if show_line_numbers:
                    rg_cmd.append("-n")
            
            # Case sensitivity
            if case_insensitive:
                rg_cmd.append("-i")
            
            # File type filter
            if file_type:
                rg_cmd.extend(["--type", file_type])
            
            # Glob pattern filter
            if glob_pattern:
                rg_cmd.extend(["--glob", glob_pattern])
            
            # Multiline support
            if multiline:
                rg_cmd.extend(["-U", "--multiline-dotall"])
            
            # Add pattern and path
            rg_cmd.append(pattern)
            rg_cmd.append(path)
            
            # Execute ripgrep
            try:
                result = subprocess.run(
                    rg_cmd,
                    capture_output=True,
                    text=True,
                    cwd=path if os.path.isdir(path) else os.path.dirname(path)
                )
                
                stdout = result.stdout
                stderr = result.stderr
                
                # Apply head limit if specified
                if head_limit and stdout:
                    lines = stdout.strip().split('\n')
                    if len(lines) > head_limit:
                        lines = lines[:head_limit]
                        stdout = '\n'.join(lines) + '\n[Output limited to first {} entries]'.format(head_limit)
                
                # Parse results based on output mode
                parsed_results = self._parse_results(stdout, output_mode)
                
                # Check if we found results
                if result.returncode == 0 and parsed_results:
                    return ToolResult.success_result(
                        data={
                            "pattern": pattern,
                            "path": path,
                            "output_mode": output_mode,
                            "results": parsed_results,
                            "count": len(parsed_results) if isinstance(parsed_results, list) else 1
                        },
                        tool_name=self.name,
                        output=self._format_output(parsed_results, output_mode, pattern)
                    )
                elif result.returncode == 1:
                    # No matches found (normal for ripgrep)
                    return ToolResult.success_result(
                        data={
                            "pattern": pattern,
                            "path": path,
                            "output_mode": output_mode,
                            "results": [],
                            "count": 0
                        },
                        tool_name=self.name,
                        output=f"No matches found for pattern: {pattern}"
                    )
                else:
                    # Error occurred
                    return ToolResult.error_result(
                        error=f"Ripgrep failed with exit code {result.returncode}: {stderr}",
                        tool_name=self.name
                    )
                    
            except FileNotFoundError:
                # Fallback to Python implementation if ripgrep not available
                return await self._fallback_search(pattern, path, glob_pattern, case_insensitive, context)
                
        except Exception as e:
            return ToolResult.error_result(
                error=f"Grep tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _parse_results(self, output: str, output_mode: str) -> List[Any]:
        """Parse ripgrep output based on mode."""
        if not output or not output.strip():
            return []
        
        lines = output.strip().split('\n')
        
        if output_mode == "files_with_matches":
            return [line.strip() for line in lines if line.strip()]
        elif output_mode == "count":
            results = []
            for line in lines:
                if ':' in line:
                    file_path, count = line.split(':', 1)
                    results.append({
                        "file": file_path.strip(),
                        "count": int(count.strip())
                    })
            return results
        else:  # content mode
            return [line for line in lines if line.strip()]
    
    def _format_output(self, results: List[Any], output_mode: str, pattern: str) -> str:
        """Format the output for display."""
        if not results:
            return f"No matches found for pattern: {pattern}"
        
        if output_mode == "files_with_matches":
            output_lines = [f"Found {len(results)} files containing '{pattern}':"]
            for file_path in results[:20]:  # Limit display
                output_lines.append(f"  {file_path}")
            if len(results) > 20:
                output_lines.append(f"  ... and {len(results) - 20} more files")
            return '\n'.join(output_lines)
        
        elif output_mode == "count":
            output_lines = [f"Match counts for pattern '{pattern}':"]
            for result in results[:20]:  # Limit display
                output_lines.append(f"  {result['file']}: {result['count']}")
            if len(results) > 20:
                output_lines.append(f"  ... and {len(results) - 20} more files")
            return '\n'.join(output_lines)
        
        else:  # content mode
            output_lines = [f"Content matches for pattern '{pattern}':"]
            for line in results[:50]:  # Limit display for content
                output_lines.append(f"  {line}")
            if len(results) > 50:
                output_lines.append(f"  ... and {len(results) - 50} more matches")
            return '\n'.join(output_lines)
    
    async def _fallback_search(self, pattern: str, path: str, glob_pattern: Optional[str], 
                             case_insensitive: bool, context: ToolContext) -> ToolResult:
        """Fallback Python implementation when ripgrep is not available."""
        try:
            import fnmatch
            
            flags = re.IGNORECASE if case_insensitive else 0
            regex = re.compile(pattern, flags)
            
            matches = []
            search_path = Path(path)
            
            if search_path.is_file():
                # Search single file
                try:
                    with open(search_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if regex.search(content):
                            matches.append(str(search_path))
                except Exception:
                    pass
            else:
                # Search directory
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        file_path = Path(root) / file
                        
                        # Apply glob filter if specified
                        if glob_pattern and not fnmatch.fnmatch(file, glob_pattern):
                            continue
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if regex.search(content):
                                    matches.append(str(file_path))
                        except Exception:
                            continue
            
            return ToolResult.success_result(
                data={
                    "pattern": pattern,
                    "path": path,
                    "results": matches,
                    "count": len(matches),
                    "fallback": True
                },
                tool_name=self.name,
                output=self._format_output(matches, "files_with_matches", pattern)
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Fallback search failed: {str(e)}",
                tool_name=self.name
            )


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "The regular expression pattern to search for in file contents"
        },
        "path": {
            "type": "string",
            "description": "File or directory to search in. Defaults to current working directory"
        },
        "glob": {
            "type": "string",
            "description": "Glob pattern to filter files (e.g. \"*.js\", \"*.{ts,tsx}\")"
        },
        "output_mode": {
            "type": "string",
            "enum": ["content", "files_with_matches", "count"],
            "description": "Output mode: content shows matching lines, files_with_matches shows file paths, count shows match counts"
        },
        "-B": {
            "type": "number",
            "description": "Number of lines to show before each match"
        },
        "-A": {
            "type": "number", 
            "description": "Number of lines to show after each match"
        },
        "-C": {
            "type": "number",
            "description": "Number of lines to show before and after each match"
        },
        "-n": {
            "type": "boolean",
            "description": "Show line numbers in output"
        },
        "-i": {
            "type": "boolean",
            "description": "Case insensitive search"
        },
        "type": {
            "type": "string",
            "description": "File type to search (js, py, rust, go, java, etc.)"
        },
        "head_limit": {
            "type": "number",
            "description": "Limit output to first N lines/entries"
        },
        "multiline": {
            "type": "boolean",
            "description": "Enable multiline mode where . matches newlines"
        }
    },
    "required": ["pattern"],
    "additionalProperties": False
}