"""
MCP Documentation Tool for Codexa.
"""

from typing import Set, Dict, Any, Optional
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPDocumentationTool(Tool):
    """Tool for retrieving documentation using MCP servers (especially Context7)."""
    
    @property
    def name(self) -> str:
        return "mcp_documentation"
    
    @property
    def description(self) -> str:
        return "Get documentation using Context7 or similar documentation servers"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"documentation", "context7", "examples", "api_reference"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"library"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        # Only handle if MCP service is available
        if not context.mcp_service or not context.mcp_service.is_running:
            return 0.0
        
        request_lower = request.lower()
        
        # High confidence for explicit documentation requests
        if any(phrase in request_lower for phrase in [
            "documentation", "docs", "api reference", "examples",
            "how to use", "usage", "guide", "tutorial"
        ]):
            return 0.8
        
        # Medium confidence for library/framework questions
        if any(phrase in request_lower for phrase in [
            "react", "vue", "angular", "python", "javascript", "typescript",
            "library", "framework", "package", "module"
        ]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute documentation retrieval."""
        try:
            # Check MCP service availability
            if not context.mcp_service or not context.mcp_service.is_running:
                return ToolResult.error_result(
                    error="MCP service not available",
                    tool_name=self.name
                )
            
            # Get parameters from context
            library = context.get_state("library")
            topic = context.get_state("topic")
            
            # Try to extract from request if not in context
            if not library:
                extracted = self._extract_documentation_parameters(context.user_request)
                library = extracted.get("library")
                topic = extracted.get("topic")
            
            if not library:
                return ToolResult.error_result(
                    error="No library specified",
                    tool_name=self.name
                )
            
            # Get documentation via MCP service
            documentation = await context.mcp_service.get_documentation(library, topic)
            
            return ToolResult.success_result(
                data={
                    "library": library,
                    "topic": topic,
                    "documentation": documentation,
                    "source": "mcp_context7"
                },
                tool_name=self.name,
                output=f"Retrieved documentation for {library}" + (f" (topic: {topic})" if topic else "")
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Documentation retrieval failed: {str(e)}",
                tool_name=self.name
            )
    
    def _extract_documentation_parameters(self, request: str) -> Dict[str, Optional[str]]:
        """Extract library and topic from request."""
        result = {"library": None, "topic": None}
        
        # Look for library names
        library_patterns = [
            r'documentation for ([a-zA-Z0-9._-]+)',
            r'docs for ([a-zA-Z0-9._-]+)',
            r'how to use ([a-zA-Z0-9._-]+)',
            r'([a-zA-Z0-9._-]+) documentation',
            r'([a-zA-Z0-9._-]+) docs'
        ]
        
        for pattern in library_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["library"] = matches[0]
                break
        
        # Look for specific topics
        topic_patterns = [
            r'about ([a-zA-Z0-9._-]+)',
            r'topic ([a-zA-Z0-9._-]+)',
            r'for ([a-zA-Z0-9._-]+)',
            r'on ([a-zA-Z0-9._-]+)'
        ]
        
        for pattern in topic_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["topic"] = matches[0]
                break
        
        return result