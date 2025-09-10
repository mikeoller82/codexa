"""
Serena-based semantic code analysis tools.
"""

from typing import Dict, Any, Set, List, Optional
import json

from ..base.tool_interface import ToolResult, ToolContext
from .base_serena_tool import BaseSerenaTool


class CodeAnalysisTool(BaseSerenaTool):
    """Tool for semantic code analysis using Serena's language server."""
    
    @property
    def name(self) -> str:
        return "serena_code_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze code structure, get symbol overviews, and understand project architecture using language server capabilities"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "code-analysis", "symbol-overview", "file-structure", 
            "semantic-analysis", "ast-analysis", "project-structure"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["get_symbols_overview", "list_dir", "find_file"]
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute semantic code analysis."""
        try:
            request = context.user_request or ""
            request_lower = request.lower()
            
            # Determine analysis type from request
            if any(word in request_lower for word in ["file structure", "symbols in file", "overview"]):
                return await self._analyze_file_symbols(context)
            elif any(word in request_lower for word in ["project structure", "project overview", "codebase"]):
                return await self._analyze_project_structure(context)
            elif any(word in request_lower for word in ["directory", "folder", "list files"]):
                return await self._analyze_directory(context)
            else:
                # Default to file analysis if current file available
                return await self._analyze_file_symbols(context)
                
        except Exception as e:
            return self._create_error_result(f"Code analysis failed: {e}")
    
    async def _analyze_file_symbols(self, context: ToolContext) -> ToolResult:
        """Analyze symbols in a specific file."""
        try:
            # Get file path from context or request
            file_path = self._extract_file_path(context)
            if not file_path:
                return self._create_error_result("No file path provided for symbol analysis")
            
            # Get symbol overview from Serena
            symbols = await self.call_serena_tool("get_symbols_overview", {
                "file_path": file_path
            })
            
            if not symbols:
                return self._create_success_result(
                    data={"symbols": [], "file_path": file_path},
                    output=f"No symbols found in {file_path}"
                )
            
            # Format results
            output = self._format_symbols_output(symbols, file_path)
            
            return self._create_success_result(
                data={
                    "symbols": symbols,
                    "file_path": file_path,
                    "symbol_count": len(symbols) if isinstance(symbols, list) else 0
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"File symbol analysis failed: {e}")
    
    async def _analyze_project_structure(self, context: ToolContext) -> ToolResult:
        """Analyze overall project structure."""
        try:
            project_path = context.current_path or "."
            
            # Get project files
            files = await self.call_serena_tool("find_file", {
                "patterns": ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.c", "*.h", "*.go"],
                "base_path": project_path
            })
            
            # Analyze key files for structure
            structure_analysis = {
                "project_path": project_path,
                "total_files": len(files) if isinstance(files, list) else 0,
                "file_types": {},
                "key_files": []
            }
            
            if isinstance(files, list):
                # Count file types
                for file_path in files:
                    ext = file_path.split('.')[-1] if '.' in file_path else 'unknown'
                    structure_analysis["file_types"][ext] = structure_analysis["file_types"].get(ext, 0) + 1
                
                # Analyze a few key files for symbols
                key_files_to_analyze = files[:5]  # First 5 files
                for file_path in key_files_to_analyze:
                    try:
                        symbols = await self.call_serena_tool("get_symbols_overview", {
                            "file_path": file_path
                        })
                        
                        if symbols:
                            structure_analysis["key_files"].append({
                                "file": file_path,
                                "symbols": len(symbols) if isinstance(symbols, list) else 0,
                                "symbols_preview": symbols[:3] if isinstance(symbols, list) else []
                            })
                    except:
                        continue  # Skip files that can't be analyzed
            
            output = self._format_project_structure_output(structure_analysis)
            
            return self._create_success_result(
                data=structure_analysis,
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Project structure analysis failed: {e}")
    
    async def _analyze_directory(self, context: ToolContext) -> ToolResult:
        """Analyze directory contents."""
        try:
            # Get directory path from context or request
            dir_path = self._extract_directory_path(context) or context.current_path or "."
            
            # List directory contents
            files = await self.call_serena_tool("list_dir", {
                "path": dir_path,
                "recursive": False
            })
            
            if not files:
                return self._create_success_result(
                    data={"files": [], "directory": dir_path},
                    output=f"No files found in {dir_path}"
                )
            
            # Format directory listing
            output = self._format_directory_output(files, dir_path)
            
            return self._create_success_result(
                data={
                    "files": files,
                    "directory": dir_path,
                    "file_count": len(files) if isinstance(files, list) else 0
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Directory analysis failed: {e}")
    
    def _extract_file_path(self, context: ToolContext) -> Optional[str]:
        """Extract file path from context or request."""
        request = context.user_request or ""
        
        # Look for file path in request
        words = request.split()
        for word in words:
            if ('.' in word and '/' in word) or word.endswith('.py') or word.endswith('.js') or word.endswith('.ts'):
                return word
        
        # Check if mentioned_files in context
        mentioned_files = getattr(context, 'mentioned_files', [])
        if mentioned_files:
            return mentioned_files[0]
        
        # Use current file if available
        if hasattr(context, 'current_file') and context.current_file:
            return context.current_file
        
        return None
    
    def _extract_directory_path(self, context: ToolContext) -> Optional[str]:
        """Extract directory path from context or request."""
        request = context.user_request or ""
        
        # Look for directory indicators
        words = request.split()
        for i, word in enumerate(words):
            if word.lower() in ["in", "from", "directory", "folder"] and i + 1 < len(words):
                return words[i + 1]
            if '/' in word and not '.' in word.split('/')[-1]:  # Path without extension
                return word
        
        return None
    
    def _format_symbols_output(self, symbols: Any, file_path: str) -> str:
        """Format symbol analysis output."""
        if not symbols:
            return f"No symbols found in {file_path}"
        
        output = [f"Symbols in {file_path}:"]
        
        if isinstance(symbols, list):
            for symbol in symbols:
                if isinstance(symbol, dict):
                    name = symbol.get('name', 'Unknown')
                    kind = symbol.get('kind', 'Unknown')
                    line = symbol.get('line', 'N/A')
                    output.append(f"  {kind}: {name} (line {line})")
                else:
                    output.append(f"  {symbol}")
        
        output.append(f"\nTotal symbols: {len(symbols) if isinstance(symbols, list) else 1}")
        return "\n".join(output)
    
    def _format_project_structure_output(self, analysis: Dict[str, Any]) -> str:
        """Format project structure analysis output."""
        output = [f"Project Structure Analysis: {analysis['project_path']}"]
        output.append(f"Total files: {analysis['total_files']}")
        
        if analysis['file_types']:
            output.append("\nFile types:")
            for ext, count in analysis['file_types'].items():
                output.append(f"  .{ext}: {count} files")
        
        if analysis['key_files']:
            output.append("\nKey files analysis:")
            for file_info in analysis['key_files']:
                output.append(f"  {file_info['file']}: {file_info['symbols']} symbols")
        
        return "\n".join(output)
    
    def _format_directory_output(self, files: Any, dir_path: str) -> str:
        """Format directory listing output."""
        output = [f"Directory: {dir_path}"]
        
        if isinstance(files, list):
            for file_item in files:
                output.append(f"  {file_item}")
        
        output.append(f"\nTotal items: {len(files) if isinstance(files, list) else 0}")
        return "\n".join(output)


class SymbolSearchTool(BaseSerenaTool):
    """Tool for searching symbols in codebase using Serena."""
    
    @property
    def name(self) -> str:
        return "serena_symbol_search"
    
    @property
    def description(self) -> str:
        return "Search for symbols (functions, classes, variables) across the codebase using semantic analysis"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "symbol-search", "semantic-search", "function-search", 
            "class-search", "variable-search", "definition-search"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["find_symbol"]
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute symbol search."""
        try:
            # Extract search query from request
            search_query = self._extract_search_query(context)
            if not search_query:
                return self._create_error_result("No search query provided")
            
            # Determine search parameters
            symbol_type = self._extract_symbol_type(context)
            local_only = "local" in (context.user_request or "").lower()
            
            # Search for symbols
            results = await self.call_serena_tool("find_symbol", {
                "query": search_query,
                "type_filter": symbol_type,
                "local": local_only
            })
            
            if not results:
                return self._create_success_result(
                    data={"results": [], "query": search_query},
                    output=f"No symbols found for '{search_query}'"
                )
            
            # Format results
            output = self._format_search_results(results, search_query, symbol_type)
            
            return self._create_success_result(
                data={
                    "results": results,
                    "query": search_query,
                    "symbol_type": symbol_type,
                    "local_only": local_only,
                    "result_count": len(results) if isinstance(results, list) else 1
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Symbol search failed: {e}")
    
    def _extract_search_query(self, context: ToolContext) -> Optional[str]:
        """Extract search query from request."""
        request = context.user_request or ""
        
        # Look for quoted strings first
        import re
        quoted = re.findall(r'"([^"]*)"', request)
        if quoted:
            return quoted[0]
        
        quoted = re.findall(r"'([^']*)'", request)  
        if quoted:
            return quoted[0]
        
        # Look for patterns like "search for X", "find X"
        patterns = [
            r'search for (\w+)',
            r'find (\w+)', 
            r'search (\w+)',
            r'look for (\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, request.lower())
            if match:
                return match.group(1)
        
        # Extract last word as potential symbol name
        words = request.split()
        if words:
            return words[-1]
        
        return None
    
    def _extract_symbol_type(self, context: ToolContext) -> Optional[str]:
        """Extract symbol type filter from request."""
        request = (context.user_request or "").lower()
        
        if any(word in request for word in ["function", "func", "method"]):
            return "function"
        elif any(word in request for word in ["class", "struct"]):
            return "class"
        elif any(word in request for word in ["variable", "var", "field"]):
            return "variable"
        elif any(word in request for word in ["constant", "const"]):
            return "constant"
        
        return None
    
    def _format_search_results(self, results: Any, query: str, symbol_type: Optional[str]) -> str:
        """Format symbol search results."""
        type_str = f" ({symbol_type})" if symbol_type else ""
        output = [f"Symbol search results for '{query}'{type_str}:"]
        
        if isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    name = result.get('name', 'Unknown')
                    kind = result.get('kind', 'Unknown')
                    location = result.get('location', {})
                    file_path = location.get('file', 'Unknown file') if isinstance(location, dict) else 'Unknown file'
                    line = location.get('line', 'N/A') if isinstance(location, dict) else 'N/A'
                    
                    output.append(f"  {kind}: {name}")
                    output.append(f"    Location: {file_path}:{line}")
                else:
                    output.append(f"  {result}")
        
        count = len(results) if isinstance(results, list) else 1
        output.append(f"\nFound {count} symbol(s)")
        return "\n".join(output)


class ReferenceSearchTool(BaseSerenaTool):
    """Tool for finding symbol references using Serena."""
    
    @property
    def name(self) -> str:
        return "serena_reference_search"
    
    @property
    def description(self) -> str:
        return "Find all references to a symbol at a specific location in the code"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "reference-search", "usage-search", "symbol-references", 
            "find-usages", "call-hierarchy"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["find_referencing_symbols"]
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute reference search."""
        try:
            # Extract location information
            location = self._extract_location(context)
            if not location:
                return self._create_error_result("File location (file:line:column) required for reference search")
            
            file_path, line, column = location
            
            # Extract reference type filter
            reference_type = self._extract_reference_type(context)
            
            # Find references
            results = await self.call_serena_tool("find_referencing_symbols", {
                "file_path": file_path,
                "line": line,
                "column": column,
                "type_filter": reference_type
            })
            
            if not results:
                return self._create_success_result(
                    data={"results": [], "location": location},
                    output=f"No references found for symbol at {file_path}:{line}:{column}"
                )
            
            # Format results
            output = self._format_reference_results(results, file_path, line, column)
            
            return self._create_success_result(
                data={
                    "results": results,
                    "location": {"file": file_path, "line": line, "column": column},
                    "reference_type": reference_type,
                    "reference_count": len(results) if isinstance(results, list) else 1
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Reference search failed: {e}")
    
    def _extract_location(self, context: ToolContext) -> Optional[tuple]:
        """Extract file:line:column location from request."""
        request = context.user_request or ""
        
        # Look for file:line:column pattern
        import re
        location_pattern = r'(\S+):(\d+):(\d+)'
        match = re.search(location_pattern, request)
        
        if match:
            file_path = match.group(1)
            line = int(match.group(2))
            column = int(match.group(3))
            return (file_path, line, column)
        
        # Look for file:line pattern (default column to 0)
        line_pattern = r'(\S+):(\d+)'
        match = re.search(line_pattern, request)
        
        if match:
            file_path = match.group(1)
            line = int(match.group(2))
            return (file_path, line, 0)
        
        return None
    
    def _extract_reference_type(self, context: ToolContext) -> Optional[str]:
        """Extract reference type filter from request."""
        request = (context.user_request or "").lower()
        
        if "read" in request:
            return "read"
        elif "write" in request:
            return "write"
        elif "call" in request:
            return "call"
        
        return None
    
    def _format_reference_results(self, results: Any, file_path: str, line: int, column: int) -> str:
        """Format reference search results."""
        output = [f"References to symbol at {file_path}:{line}:{column}:"]
        
        if isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    location = result.get('location', {})
                    ref_file = location.get('file', 'Unknown file') if isinstance(location, dict) else 'Unknown file'
                    ref_line = location.get('line', 'N/A') if isinstance(location, dict) else 'N/A'
                    ref_type = result.get('type', 'reference')
                    context_text = result.get('context', '')
                    
                    output.append(f"  {ref_type}: {ref_file}:{ref_line}")
                    if context_text:
                        output.append(f"    Context: {context_text}")
                else:
                    output.append(f"  {result}")
        
        count = len(results) if isinstance(results, list) else 1
        output.append(f"\nFound {count} reference(s)")
        return "\n".join(output)