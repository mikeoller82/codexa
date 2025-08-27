"""
MCP Health Check Tool for Codexa.
"""

from typing import Set, Dict, Any

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPHealthCheckTool(Tool):
    """Tool for monitoring MCP server health and performance."""
    
    @property
    def name(self) -> str:
        return "mcp_health_check"
    
    @property
    def description(self) -> str:
        return "Monitor MCP server health, performance, and availability"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"health_monitoring", "performance", "diagnostics", "status_check"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit health check requests
        if any(phrase in request_lower for phrase in [
            "health check", "mcp health", "server health", "check status",
            "mcp status", "server status", "diagnostics"
        ]):
            return 0.9
        
        # Medium confidence for monitoring keywords
        if any(phrase in request_lower for phrase in [
            "health", "status", "check", "monitor"
        ]) and any(word in request_lower for word in ["mcp", "server"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute health check."""
        try:
            # Get server name from context if specified
            server_name = context.get_state("server_name")
            detailed = context.get_state("detailed", False)
            
            # Perform health check
            health_data = await self._perform_health_check(server_name, detailed, context)
            
            # Determine overall health status
            overall_status = self._determine_overall_status(health_data)
            
            return ToolResult.success_result(
                data={
                    "overall_status": overall_status,
                    "health_data": health_data,
                    "timestamp": health_data.get("timestamp"),
                    "checked_servers": health_data.get("checked_servers", 0)
                },
                tool_name=self.name,
                output=f"MCP health check: {overall_status.upper()}"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Health check failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _perform_health_check(self, server_name: str, detailed: bool, 
                                  context: ToolContext) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        from datetime import datetime
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "mcp_service_available": False,
            "servers": {},
            "overall_metrics": {}
        }
        
        # Check if MCP service is available
        if not context.mcp_service:
            health_data["error"] = "MCP service not initialized"
            return health_data
        
        health_data["mcp_service_available"] = True
        health_data["mcp_service_running"] = context.mcp_service.is_running
        
        try:
            # Get service status
            service_status = context.mcp_service.get_service_status()
            health_data["service_status"] = service_status
            
            # Get available servers
            available_servers = context.mcp_service.get_available_servers()
            health_data["available_servers"] = available_servers
            health_data["checked_servers"] = len(available_servers)
            
            # Check specific server or all servers
            servers_to_check = [server_name] if server_name else available_servers
            
            for server in servers_to_check:
                if server in available_servers:
                    server_health = await self._check_server_health(server, context)
                    health_data["servers"][server] = server_health
            
            # Calculate overall metrics
            health_data["overall_metrics"] = self._calculate_overall_metrics(health_data["servers"])
            
        except Exception as e:
            health_data["error"] = str(e)
        
        return health_data
    
    async def _check_server_health(self, server_name: str, context: ToolContext) -> Dict[str, Any]:
        """Check health of a specific server."""
        server_health = {
            "name": server_name,
            "available": False,
            "responsive": False,
            "error": None
        }
        
        try:
            # Get server capabilities
            capabilities = context.mcp_service.get_server_capabilities(server_name)
            server_health["available"] = bool(capabilities)
            server_health["capabilities"] = capabilities
            
            # Test server responsiveness with a simple query
            if server_health["available"]:
                try:
                    # Send a lightweight test query
                    test_result = await context.mcp_service.query_server(
                        "health_check",
                        preferred_server=server_name,
                        context={"type": "health_check", "lightweight": True}
                    )
                    server_health["responsive"] = True
                    server_health["test_result"] = "success"
                except Exception as e:
                    server_health["responsive"] = False
                    server_health["test_error"] = str(e)
            
        except Exception as e:
            server_health["error"] = str(e)
        
        return server_health
    
    def _calculate_overall_metrics(self, servers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall health metrics from individual server data."""
        if not servers:
            return {"healthy_servers": 0, "total_servers": 0, "health_percentage": 0}
        
        total_servers = len(servers)
        available_servers = sum(1 for server in servers.values() if server.get("available", False))
        responsive_servers = sum(1 for server in servers.values() if server.get("responsive", False))
        healthy_servers = sum(1 for server in servers.values() 
                            if server.get("available", False) and server.get("responsive", False))
        
        return {
            "total_servers": total_servers,
            "available_servers": available_servers,
            "responsive_servers": responsive_servers,
            "healthy_servers": healthy_servers,
            "health_percentage": (healthy_servers / total_servers * 100) if total_servers > 0 else 0,
            "availability_percentage": (available_servers / total_servers * 100) if total_servers > 0 else 0,
            "responsiveness_percentage": (responsive_servers / total_servers * 100) if total_servers > 0 else 0
        }
    
    def _determine_overall_status(self, health_data: Dict[str, Any]) -> str:
        """Determine overall health status."""
        if not health_data.get("mcp_service_available", False):
            return "critical"
        
        if not health_data.get("mcp_service_running", False):
            return "down"
        
        metrics = health_data.get("overall_metrics", {})
        health_percentage = metrics.get("health_percentage", 0)
        
        if health_percentage >= 90:
            return "healthy"
        elif health_percentage >= 70:
            return "degraded"
        elif health_percentage >= 50:
            return "warning"
        else:
            return "critical"