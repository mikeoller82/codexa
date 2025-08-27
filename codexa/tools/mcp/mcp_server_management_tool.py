"""
MCP Server Management Tool for Codexa.
"""

from typing import Set, Dict, Any, List
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPServerManagementTool(Tool):
    """Tool for managing MCP servers (enable, disable, restart, configure)."""
    
    @property
    def name(self) -> str:
        return "mcp_server_management"
    
    @property
    def description(self) -> str:
        return "Manage MCP servers - enable, disable, restart, and configure"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"server_management", "configuration", "enable_disable", "restart"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"action"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit server management requests
        if any(phrase in request_lower for phrase in [
            "enable mcp", "disable mcp", "restart mcp", "mcp server",
            "start server", "stop server", "configure mcp"
        ]):
            return 0.9
        
        # Medium confidence for server management keywords
        if any(phrase in request_lower for phrase in [
            "enable", "disable", "restart", "start", "stop"
        ]) and any(word in request_lower for word in ["server", "mcp"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute server management action."""
        try:
            # Get parameters from context
            action = context.get_state("action")
            server_name = context.get_state("server_name")
            
            # Try to extract from request if not in context
            if not action or not server_name:
                extracted = self._extract_management_parameters(context.user_request)
                action = action or extracted.get("action")
                server_name = server_name or extracted.get("server_name")
            
            if not action:
                return ToolResult.error_result(
                    error="No action specified",
                    tool_name=self.name
                )
            
            # Execute management action
            result = await self._execute_management_action(action, server_name, context)
            
            return ToolResult.success_result(
                data=result,
                tool_name=self.name,
                output=f"MCP server management: {action}" + (f" {server_name}" if server_name else "")
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Server management failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _execute_management_action(self, action: str, server_name: str, 
                                       context: ToolContext) -> Dict[str, Any]:
        """Execute the management action."""
        result = {"action": action, "server_name": server_name, "success": False}
        
        if not context.mcp_service:
            result["error"] = "MCP service not available"
            return result
        
        try:
            if action.lower() in ["enable", "start"]:
                if server_name:
                    success = context.mcp_service.enable_server(server_name)
                    result["success"] = success
                    result["message"] = f"Server {server_name} {'enabled' if success else 'failed to enable'}"
                else:
                    result["error"] = "Server name required for enable action"
            
            elif action.lower() in ["disable", "stop"]:
                if server_name:
                    success = context.mcp_service.disable_server(server_name)
                    result["success"] = success
                    result["message"] = f"Server {server_name} {'disabled' if success else 'failed to disable'}"
                else:
                    result["error"] = "Server name required for disable action"
            
            elif action.lower() in ["restart", "reload"]:
                if server_name:
                    success = await context.mcp_service.restart_server(server_name)
                    result["success"] = success
                    result["message"] = f"Server {server_name} {'restarted' if success else 'failed to restart'}"
                else:
                    result["error"] = "Server name required for restart action"
            
            elif action.lower() in ["status", "info"]:
                if server_name:
                    capabilities = context.mcp_service.get_server_capabilities(server_name)
                    result["success"] = True
                    result["capabilities"] = capabilities
                    result["message"] = f"Retrieved status for {server_name}"
                else:
                    status = context.mcp_service.get_service_status()
                    result["success"] = True
                    result["status"] = status
                    result["message"] = "Retrieved overall MCP service status"
            
            elif action.lower() in ["list", "show"]:
                available_servers = context.mcp_service.get_available_servers()
                result["success"] = True
                result["servers"] = available_servers
                result["message"] = f"Found {len(available_servers)} available servers"
            
            else:
                result["error"] = f"Unknown action: {action}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _extract_management_parameters(self, request: str) -> Dict[str, str]:
        """Extract management parameters from request."""
        result = {"action": "", "server_name": ""}
        
        request_lower = request.lower()
        
        # Detect action
        if any(word in request_lower for word in ["enable", "start"]):
            result["action"] = "enable"
        elif any(word in request_lower for word in ["disable", "stop"]):
            result["action"] = "disable"
        elif any(word in request_lower for word in ["restart", "reload"]):
            result["action"] = "restart"
        elif any(word in request_lower for word in ["status", "info"]):
            result["action"] = "status"
        elif any(word in request_lower for word in ["list", "show"]):
            result["action"] = "list"
        
        # Extract server name
        server_patterns = [
            r'server ([a-zA-Z0-9_-]+)',
            r'mcp ([a-zA-Z0-9_-]+)',
            r'(context7|sequential|magic|playwright)',
        ]
        
        for pattern in server_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["server_name"] = matches[0]
                break
        
        return result