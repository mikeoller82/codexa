"""
MCP Configuration Tool for Codexa.
"""

from typing import Set, Dict, Any, List
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPConfigurationTool(Tool):
    """Tool for configuring MCP servers and settings."""
    
    @property
    def name(self) -> str:
        return "mcp_configuration"
    
    @property
    def description(self) -> str:
        return "Configure MCP servers, add custom servers, and manage settings"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"configuration", "settings", "custom_servers", "server_management"}
    
    @property
    def required_context(self) -> Set[str]:
        return set()  # Can extract action from user request
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit configuration requests
        if any(phrase in request_lower for phrase in [
            "configure mcp", "mcp config", "mcp settings", "add server",
            "custom server", "server config", "mcp setup"
        ]):
            return 0.9
        
        # Medium confidence for configuration keywords
        if any(phrase in request_lower for phrase in [
            "configure", "config", "setup", "add"
        ]) and any(word in request_lower for word in ["mcp", "server"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute MCP configuration."""
        try:
            # Get parameters from context
            action = context.get_state("action")
            server_name = context.get_state("server_name")
            server_config = context.get_state("server_config", {})
            
            # Try to extract from request if not in context
            if not action:
                extracted = self._extract_config_parameters(context.user_request)
                action = extracted.get("action")
                server_name = extracted.get("server_name")
                server_config = extracted.get("server_config", {})
            
            if not action:
                return ToolResult.error_result(
                    error="No configuration action specified",
                    tool_name=self.name
                )
            
            # Execute configuration action
            result = await self._execute_config_action(action, server_name, server_config, context)
            
            return ToolResult.success_result(
                data=result,
                tool_name=self.name,
                output=f"MCP configuration: {action} " + result.get("message", "completed")
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Configuration failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _execute_config_action(self, action: str, server_name: str, 
                                   server_config: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Execute configuration action."""
        result = {"action": action, "server_name": server_name}
        
        if not context.mcp_service:
            result["error"] = "MCP service not available"
            return result
        
        try:
            if action.lower() in ["add", "create"]:
                result.update(await self._add_custom_server(server_name, server_config, context))
            
            elif action.lower() in ["remove", "delete"]:
                result.update(await self._remove_server(server_name, context))
            
            elif action.lower() in ["update", "modify"]:
                result.update(await self._update_server_config(server_name, server_config, context))
            
            elif action.lower() in ["list", "show"]:
                result.update(await self._list_server_configs(context))
            
            elif action.lower() in ["get", "info"]:
                result.update(await self._get_server_config(server_name, context))
            
            elif action.lower() in ["validate", "test"]:
                result.update(await self._validate_server_config(server_name, server_config, context))
            
            else:
                result["error"] = f"Unknown configuration action: {action}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _add_custom_server(self, server_name: str, server_config: Dict[str, Any], 
                               context: ToolContext) -> Dict[str, Any]:
        """Add a custom MCP server."""
        add_result = {
            "add_server": True,
            "success": False
        }
        
        if not server_name:
            add_result["error"] = "Server name required"
            return add_result
        
        if not server_config.get("command"):
            add_result["error"] = "Server command required in configuration"
            return add_result
        
        try:
            # Add custom server via MCP service
            success = context.mcp_service.add_custom_server(
                name=server_name,
                command=server_config["command"],
                capabilities=server_config.get("capabilities", []),
                **{k: v for k, v in server_config.items() if k not in ["command", "capabilities"]}
            )
            
            add_result["success"] = success
            add_result["message"] = f"Server {server_name} {'added' if success else 'failed to add'}"
            add_result["server_config"] = server_config
            
        except Exception as e:
            add_result["error"] = str(e)
            add_result["message"] = f"Failed to add server: {str(e)}"
        
        return add_result
    
    async def _remove_server(self, server_name: str, context: ToolContext) -> Dict[str, Any]:
        """Remove a server configuration."""
        remove_result = {
            "remove_server": True,
            "success": False
        }
        
        if not server_name:
            remove_result["error"] = "Server name required"
            return remove_result
        
        try:
            # Disable server first
            context.mcp_service.disable_server(server_name)
            
            # Note: Actual removal would depend on MCP service implementation
            # For now, just disable
            remove_result["success"] = True
            remove_result["message"] = f"Server {server_name} disabled (removal not fully implemented)"
            
        except Exception as e:
            remove_result["error"] = str(e)
            remove_result["message"] = f"Failed to remove server: {str(e)}"
        
        return remove_result
    
    async def _update_server_config(self, server_name: str, server_config: Dict[str, Any],
                                  context: ToolContext) -> Dict[str, Any]:
        """Update server configuration."""
        update_result = {
            "update_server": True,
            "success": False
        }
        
        if not server_name:
            update_result["error"] = "Server name required"
            return update_result
        
        try:
            # For now, this would require removing and re-adding the server
            # with new configuration
            update_result["success"] = False
            update_result["message"] = "Server configuration update not fully implemented"
            update_result["suggestion"] = "Remove and re-add the server with new configuration"
            
        except Exception as e:
            update_result["error"] = str(e)
            update_result["message"] = f"Failed to update server: {str(e)}"
        
        return update_result
    
    async def _list_server_configs(self, context: ToolContext) -> Dict[str, Any]:
        """List all server configurations."""
        list_result = {
            "list_servers": True,
            "success": True
        }
        
        try:
            # Get available servers
            available_servers = context.mcp_service.get_available_servers()
            
            # Get capabilities for each server
            server_info = {}
            for server in available_servers:
                capabilities = context.mcp_service.get_server_capabilities(server)
                server_info[server] = {
                    "capabilities": capabilities,
                    "available": True
                }
            
            list_result["servers"] = server_info
            list_result["server_count"] = len(server_info)
            list_result["message"] = f"Found {len(server_info)} configured servers"
            
        except Exception as e:
            list_result["success"] = False
            list_result["error"] = str(e)
            list_result["message"] = f"Failed to list servers: {str(e)}"
        
        return list_result
    
    async def _get_server_config(self, server_name: str, context: ToolContext) -> Dict[str, Any]:
        """Get configuration for a specific server."""
        get_result = {
            "get_server_config": True,
            "success": False
        }
        
        if not server_name:
            get_result["error"] = "Server name required"
            return get_result
        
        try:
            capabilities = context.mcp_service.get_server_capabilities(server_name)
            available_servers = context.mcp_service.get_available_servers()
            
            get_result["success"] = True
            get_result["server_config"] = {
                "name": server_name,
                "capabilities": capabilities,
                "available": server_name in available_servers
            }
            get_result["message"] = f"Retrieved configuration for {server_name}"
            
        except Exception as e:
            get_result["error"] = str(e)
            get_result["message"] = f"Failed to get server config: {str(e)}"
        
        return get_result
    
    async def _validate_server_config(self, server_name: str, server_config: Dict[str, Any],
                                    context: ToolContext) -> Dict[str, Any]:
        """Validate server configuration."""
        validate_result = {
            "validate_config": True,
            "success": True,
            "validation_errors": []
        }
        
        # Basic validation
        if server_name and not server_name.replace('_', '').replace('-', '').isalnum():
            validate_result["validation_errors"].append("Server name contains invalid characters")
        
        if server_config:
            if not server_config.get("command"):
                validate_result["validation_errors"].append("Server command is required")
            
            if "capabilities" in server_config and not isinstance(server_config["capabilities"], list):
                validate_result["validation_errors"].append("Capabilities must be a list")
        
        validate_result["success"] = len(validate_result["validation_errors"]) == 0
        validate_result["message"] = (
            "Configuration valid" if validate_result["success"] 
            else f"Validation failed: {len(validate_result['validation_errors'])} errors"
        )
        
        return validate_result
    
    def _extract_config_parameters(self, request: str) -> Dict[str, Any]:
        """Extract configuration parameters from request."""
        result = {
            "action": "",
            "server_name": "",
            "server_config": {}
        }
        
        request_lower = request.lower()
        
        # Detect action
        if any(word in request_lower for word in ["add", "create"]):
            result["action"] = "add"
        elif any(word in request_lower for word in ["remove", "delete"]):
            result["action"] = "remove"
        elif any(word in request_lower for word in ["update", "modify"]):
            result["action"] = "update"
        elif any(word in request_lower for word in ["list", "show"]):
            result["action"] = "list"
        elif any(word in request_lower for word in ["get", "info"]):
            result["action"] = "get"
        elif any(word in request_lower for word in ["validate", "test"]):
            result["action"] = "validate"
        
        # Extract server name
        server_patterns = [
            r'server ([a-zA-Z0-9_-]+)',
            r'add ([a-zA-Z0-9_-]+)',
            r'create ([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in server_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["server_name"] = matches[0]
                break
        
        # Extract basic config from patterns (simplified)
        if "command" in request_lower:
            command_match = re.search(r'command[:\s]+([^\s]+)', request, re.IGNORECASE)
            if command_match:
                result["server_config"]["command"] = command_match.group(1)
        
        return result