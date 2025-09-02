"""
MCP Routing Tool for Codexa.
"""

from typing import Set, Dict, Any, List

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPRoutingTool(Tool):
    """Tool for diagnosing MCP server routing and finding optimal servers."""
    
    @property
    def name(self) -> str:
        return "mcp_routing"
    
    @property
    def description(self) -> str:
        return "Diagnose MCP server routing and find optimal servers for requests"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"routing", "diagnostics", "optimization", "server_selection"}
    
    @property
    def required_context(self) -> Set[str]:
        return set()  # Uses user_request as fallback
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit routing requests
        if any(phrase in request_lower for phrase in [
            "mcp routing", "server routing", "diagnose routing", "which server",
            "best server", "optimal server", "route to server"
        ]):
            return 0.9
        
        # Medium confidence for diagnostic keywords
        if any(phrase in request_lower for phrase in [
            "diagnose", "routing", "server selection", "which", "best"
        ]) and any(word in request_lower for word in ["mcp", "server"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute routing diagnosis."""
        try:
            # Get parameters from context
            request_to_route = context.get_state("request", context.user_request)
            
            # Perform routing analysis
            routing_analysis = await self._analyze_routing(request_to_route, context)
            
            return ToolResult.success_result(
                data=routing_analysis,
                tool_name=self.name,
                output=f"Routing analysis complete for: {request_to_route[:50]}..."
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Routing analysis failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _analyze_routing(self, request: str, context: ToolContext) -> Dict[str, Any]:
        """Analyze routing options for a request."""
        analysis = {
            "request": request,
            "available_servers": [],
            "routing_options": [],
            "recommended_server": None,
            "routing_explanation": []
        }
        
        if not context.mcp_service or not context.mcp_service.is_running:
            analysis["error"] = "MCP service not available"
            return analysis
        
        try:
            # Get available servers
            available_servers = context.mcp_service.get_available_servers()
            analysis["available_servers"] = available_servers
            
            # Get server capabilities
            server_capabilities = {}
            for server in available_servers:
                capabilities = context.mcp_service.get_server_capabilities(server)
                server_capabilities[server] = capabilities
            
            analysis["server_capabilities"] = server_capabilities
            
            # Use MCP service's routing diagnosis if available
            if hasattr(context.mcp_service, 'diagnose_routing'):
                routing_diagnosis = context.mcp_service.diagnose_routing(request)
                analysis.update(routing_diagnosis)
            else:
                # Fallback: simple routing analysis
                analysis.update(self._simple_routing_analysis(request, server_capabilities))
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    def _simple_routing_analysis(self, request: str, 
                                server_capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Simple routing analysis when advanced diagnosis is not available."""
        request_lower = request.lower()
        routing_options = []
        
        # Simple keyword-based routing
        routing_rules = {
            "context7": ["documentation", "docs", "api", "reference", "examples"],
            "sequential": ["analyze", "debug", "complex", "reasoning", "analysis"],
            "magic": ["component", "ui", "generate", "interface", "design"],
            "playwright": ["test", "e2e", "browser", "automation", "validation"]
        }
        
        for server, keywords in routing_rules.items():
            if server in server_capabilities:
                score = sum(1 for keyword in keywords if keyword in request_lower)
                if score > 0:
                    routing_options.append({
                        "server": server,
                        "score": score,
                        "matched_keywords": [kw for kw in keywords if kw in request_lower],
                        "capabilities": server_capabilities[server]
                    })
        
        # Sort by score (highest first)
        routing_options.sort(key=lambda x: x["score"], reverse=True)
        
        # Generate explanations
        explanations = []
        for option in routing_options:
            explanations.append(
                f"{option['server']}: Score {option['score']} "
                f"(matched: {', '.join(option['matched_keywords'])})"
            )
        
        return {
            "routing_options": routing_options,
            "recommended_server": routing_options[0]["server"] if routing_options else None,
            "routing_explanation": explanations
        }