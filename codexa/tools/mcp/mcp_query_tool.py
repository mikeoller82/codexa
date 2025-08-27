"""
MCP Query Tool for Codexa.
"""

from typing import Set, Dict, Any, Optional, List
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPQueryTool(Tool):
    """Tool for querying MCP servers with intelligent routing."""
    
    @property
    def name(self) -> str:
        return "mcp_query"
    
    @property
    def description(self) -> str:
        return "Query MCP servers with intelligent routing and fallback"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"query", "mcp", "server_communication", "intelligent_routing"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"query"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        # Only handle if MCP service is available
        if not context.mcp_service or not context.mcp_service.is_running:
            return 0.0
        
        request_lower = request.lower()
        
        # High confidence for explicit MCP queries
        if any(phrase in request_lower for phrase in [
            "query mcp", "ask mcp", "mcp server", "use mcp"
        ]):
            return 0.9
        
        # Medium confidence for tasks that benefit from MCP
        if any(phrase in request_lower for phrase in [
            "documentation", "analyze code", "generate ui", "component",
            "test", "examples", "patterns"
        ]):
            return 0.4
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute MCP query."""
        try:
            # Check MCP service availability
            if not context.mcp_service or not context.mcp_service.is_running:
                return ToolResult.error_result(
                    error="MCP service not available",
                    tool_name=self.name
                )
            
            # Get query parameters from context
            query = context.get_state("query")
            preferred_server = context.get_state("preferred_server")
            required_capabilities = context.get_state("required_capabilities", [])
            query_context = context.get_state("query_context", {})
            
            # Extract from request if not in context
            if not query:
                query = context.user_request
            
            if not query:
                return ToolResult.error_result(
                    error="No query specified",
                    tool_name=self.name
                )
            
            # Execute MCP query
            result = await context.mcp_service.query_server(
                request=query,
                preferred_server=preferred_server,
                required_capabilities=required_capabilities,
                context=query_context
            )
            
            return ToolResult.success_result(
                data={
                    "query": query,
                    "result": result,
                    "server_used": self._extract_server_from_result(result),
                    "capabilities_used": required_capabilities
                },
                tool_name=self.name,
                output=f"MCP query successful: {query}"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"MCP query failed: {str(e)}",
                tool_name=self.name
            )
    
    def _extract_server_from_result(self, result: Any) -> str:
        """Extract server name from result if available."""
        if isinstance(result, dict) and "server_name" in result:
            return result["server_name"]
        return "unknown"