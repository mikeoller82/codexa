"""
MCP Connection Tool for Codexa.
"""

from typing import Set, Dict, Any

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPConnectionTool(Tool):
    """Tool for managing MCP server connections."""
    
    @property
    def name(self) -> str:
        return "mcp_connection"
    
    @property
    def description(self) -> str:
        return "Manage MCP server connections and connection diagnostics"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"connection", "networking", "diagnostics", "troubleshooting"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit connection requests
        if any(phrase in request_lower for phrase in [
            "mcp connection", "server connection", "connection test", "connect to",
            "connection status", "network test", "connectivity"
        ]):
            return 0.9
        
        # Medium confidence for connection-related keywords
        if any(phrase in request_lower for phrase in [
            "connection", "connect", "network", "connectivity"
        ]) and any(word in request_lower for word in ["mcp", "server"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute connection management."""
        try:
            # Get parameters from context
            action = context.get_state("action", "test")
            server_name = context.get_state("server_name")
            
            # Extract from request if not in context
            if not server_name:
                extracted = self._extract_connection_parameters(context.user_request)
                action = extracted.get("action", action)
                server_name = extracted.get("server_name")
            
            # Execute connection action
            result = await self._execute_connection_action(action, server_name, context)
            
            return ToolResult.success_result(
                data=result,
                tool_name=self.name,
                output=f"Connection {action}: " + result.get("message", "completed")
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Connection management failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _execute_connection_action(self, action: str, server_name: str, 
                                       context: ToolContext) -> Dict[str, Any]:
        """Execute connection action."""
        result = {"action": action, "server_name": server_name}
        
        if not context.mcp_service:
            result["error"] = "MCP service not available"
            result["message"] = "MCP service not initialized"
            return result
        
        try:
            if action.lower() in ["test", "check", "ping"]:
                result.update(await self._test_connection(server_name, context))
            
            elif action.lower() in ["connect", "start"]:
                result.update(await self._establish_connection(server_name, context))
            
            elif action.lower() in ["disconnect", "stop"]:
                result.update(await self._close_connection(server_name, context))
            
            elif action.lower() in ["status", "info"]:
                result.update(await self._get_connection_status(server_name, context))
            
            else:
                result["error"] = f"Unknown connection action: {action}"
                result["message"] = f"Unsupported action: {action}"
        
        except Exception as e:
            result["error"] = str(e)
            result["message"] = f"Action failed: {str(e)}"
        
        return result
    
    async def _test_connection(self, server_name: str, context: ToolContext) -> Dict[str, Any]:
        """Test connection to MCP server."""
        test_result = {
            "connection_test": True,
            "success": False
        }
        
        try:
            if server_name:
                # Test specific server
                available_servers = context.mcp_service.get_available_servers()
                if server_name in available_servers:
                    # Try a simple query to test connectivity
                    test_query = await context.mcp_service.query_server(
                        "connection_test",
                        preferred_server=server_name,
                        context={"type": "connection_test"}
                    )
                    test_result["success"] = True
                    test_result["message"] = f"Connection to {server_name} successful"
                    test_result["test_response"] = test_query
                else:
                    test_result["message"] = f"Server {server_name} not available"
                    test_result["available_servers"] = available_servers
            else:
                # Test MCP service overall
                service_status = context.mcp_service.get_service_status()
                test_result["success"] = service_status.get("running", False)
                test_result["message"] = f"MCP service status: {'running' if test_result['success'] else 'not running'}"
                test_result["service_status"] = service_status
        
        except Exception as e:
            test_result["message"] = f"Connection test failed: {str(e)}"
            test_result["test_error"] = str(e)
        
        return test_result
    
    async def _establish_connection(self, server_name: str, context: ToolContext) -> Dict[str, Any]:
        """Establish connection to MCP server."""
        connect_result = {
            "connection_establish": True,
            "success": False
        }
        
        try:
            if server_name:
                # Enable/start specific server
                success = context.mcp_service.enable_server(server_name)
                connect_result["success"] = success
                connect_result["message"] = f"Server {server_name} {'connected' if success else 'failed to connect'}"
            else:
                # Start MCP service
                if not context.mcp_service.is_running:
                    success = await context.mcp_service.start()
                    connect_result["success"] = success
                    connect_result["message"] = f"MCP service {'started' if success else 'failed to start'}"
                else:
                    connect_result["success"] = True
                    connect_result["message"] = "MCP service already running"
        
        except Exception as e:
            connect_result["message"] = f"Connection establishment failed: {str(e)}"
            connect_result["connect_error"] = str(e)
        
        return connect_result
    
    async def _close_connection(self, server_name: str, context: ToolContext) -> Dict[str, Any]:
        """Close connection to MCP server."""
        disconnect_result = {
            "connection_close": True,
            "success": False
        }
        
        try:
            if server_name:
                # Disable specific server
                success = context.mcp_service.disable_server(server_name)
                disconnect_result["success"] = success
                disconnect_result["message"] = f"Server {server_name} {'disconnected' if success else 'failed to disconnect'}"
            else:
                # Stop MCP service
                await context.mcp_service.stop()
                disconnect_result["success"] = True
                disconnect_result["message"] = "MCP service stopped"
        
        except Exception as e:
            disconnect_result["message"] = f"Connection close failed: {str(e)}"
            disconnect_result["disconnect_error"] = str(e)
        
        return disconnect_result
    
    async def _get_connection_status(self, server_name: str, context: ToolContext) -> Dict[str, Any]:
        """Get connection status."""
        status_result = {
            "connection_status": True,
            "success": True
        }
        
        try:
            if server_name:
                # Get specific server status
                available_servers = context.mcp_service.get_available_servers()
                capabilities = context.mcp_service.get_server_capabilities(server_name)
                
                status_result["server_available"] = server_name in available_servers
                status_result["server_capabilities"] = capabilities
                status_result["message"] = f"Status for {server_name}: {'available' if server_name in available_servers else 'not available'}"
            else:
                # Get overall service status
                service_status = context.mcp_service.get_service_status()
                status_result["service_status"] = service_status
                status_result["message"] = f"MCP service status retrieved"
        
        except Exception as e:
            status_result["success"] = False
            status_result["message"] = f"Status check failed: {str(e)}"
            status_result["status_error"] = str(e)
        
        return status_result
    
    def _extract_connection_parameters(self, request: str) -> Dict[str, str]:
        """Extract connection parameters from request."""
        import re
        
        result = {"action": "test", "server_name": ""}
        
        request_lower = request.lower()
        
        # Detect action
        if any(word in request_lower for word in ["test", "check", "ping"]):
            result["action"] = "test"
        elif any(word in request_lower for word in ["connect", "start", "enable"]):
            result["action"] = "connect"
        elif any(word in request_lower for word in ["disconnect", "stop", "disable"]):
            result["action"] = "disconnect"
        elif any(word in request_lower for word in ["status", "info"]):
            result["action"] = "status"
        
        # Extract server name
        server_patterns = [
            r'server ([a-zA-Z0-9_-]+)',
            r'(context7|sequential|magic|playwright)',
            r'to ([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in server_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["server_name"] = matches[0]
                break
        
        return result