"""
MCP Code Analysis Tool for Codexa.
"""

from typing import Set, Dict, Any, Optional
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPCodeAnalysisTool(Tool):
    """Tool for analyzing code using MCP servers (especially Sequential)."""
    
    @property
    def name(self) -> str:
        return "mcp_code_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze code using Sequential or analysis-capable servers"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"analysis", "sequential", "code_review", "debugging"}
    
    @property
    def required_context(self) -> Set[str]:
        return set()  # Can extract code from user request or file path
    
    @property
    def dependencies(self) -> Set[str]:
        return {"read_file"}  # May need to read code from files
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        # Only handle if MCP service is available
        if not context.mcp_service or not context.mcp_service.is_running:
            return 0.0
        
        request_lower = request.lower()
        
        # High confidence for explicit analysis requests
        if any(phrase in request_lower for phrase in [
            "analyze code", "review code", "code analysis", "code review",
            "debug", "find issues", "check code", "examine code"
        ]):
            return 0.9
        
        # Medium confidence for analysis-related keywords
        if any(phrase in request_lower for phrase in [
            "analyze", "review", "debug", "issues", "problems",
            "improvements", "optimize", "refactor"
        ]) and any(word in request_lower for word in ["code", "file", "function"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute code analysis."""
        try:
            # Check MCP service availability
            if not context.mcp_service or not context.mcp_service.is_running:
                return ToolResult.error_result(
                    error="MCP service not available",
                    tool_name=self.name
                )
            
            # Get parameters from context
            code = context.get_state("code")
            analysis_context = context.get_state("analysis_context")
            file_path = context.get_state("file_path")
            
            # Try to get code from file if not provided directly
            if not code and file_path:
                # Try to read file using read_file tool
                read_context = ToolContext(
                    request_id=context.request_id,
                    user_request=f"read {file_path}",
                    session_id=context.session_id,
                    current_dir=context.current_dir,
                    config=context.config,
                    mcp_service=context.mcp_service,
                    provider=context.provider
                )
                read_context.update_state("file_path", file_path)
                
                # Import and use read_file tool
                from ..filesystem.read_file_tool import ReadFileTool
                read_tool = ReadFileTool()
                read_result = await read_tool.execute(read_context)
                
                if read_result.success:
                    code = read_result.data.get("content")
                else:
                    return ToolResult.error_result(
                        error=f"Failed to read file for analysis: {read_result.error}",
                        tool_name=self.name
                    )
            
            # Extract from request if still no code
            if not code:
                extracted = self._extract_analysis_parameters(context.user_request)
                code = extracted.get("code")
                analysis_context = analysis_context or extracted.get("context")
            
            if not code:
                return ToolResult.error_result(
                    error="No code specified for analysis",
                    tool_name=self.name
                )
            
            # Perform analysis via MCP service
            analysis_result = await context.mcp_service.analyze_code(code, analysis_context)
            
            return ToolResult.success_result(
                data={
                    "code_length": len(code),
                    "analysis": analysis_result,
                    "context": analysis_context,
                    "file_path": file_path
                },
                tool_name=self.name,
                output=f"Code analysis complete ({len(code)} characters analyzed)"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Code analysis failed: {str(e)}",
                tool_name=self.name
            )
    
    def _extract_analysis_parameters(self, request: str) -> Dict[str, Optional[str]]:
        """Extract code and context from request."""
        result = {"code": None, "context": None}
        
        # Look for code blocks
        code_patterns = [
            r'```([^`]+)```',  # Code blocks
            r'`([^`]+)`',      # Inline code
            r'"([^"]{50,})"',  # Long quoted strings (likely code)
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, request, re.DOTALL)
            if matches:
                result["code"] = matches[0].strip()
                break
        
        # Look for context about what to analyze
        context_patterns = [
            r'analyze for ([^.]+)',
            r'check for ([^.]+)',
            r'find ([^.]+)',
            r'look for ([^.]+)'
        ]
        
        for pattern in context_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["context"] = matches[0].strip()
                break
        
        return result