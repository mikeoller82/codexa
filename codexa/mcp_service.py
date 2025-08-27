"""
MCP integration service for Codexa with intelligent server coordination.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

from .mcp.connection_manager import MCPConnectionManager, MCPServerConfig
from .mcp.server_registry import MCPServerRegistry, CapabilityMatch
from .mcp.health_monitor import MCPHealthMonitor, HealthStatus
from .mcp.protocol import MCPError
from .enhanced_config import EnhancedConfig, MCPServerConfig as ConfigMCPServer


class MCPService:
    """Main MCP integration service for Codexa."""
    
    def __init__(self, config: EnhancedConfig):
        self.config = config
        self.logger = logging.getLogger("codexa.mcp")
        
        # Core MCP components
        self.connection_manager = MCPConnectionManager()
        self.server_registry = MCPServerRegistry(self.connection_manager)
        self.health_monitor = MCPHealthMonitor(self.connection_manager)
        
        # Service state
        self.is_running = False
        self.startup_time: Optional[datetime] = None
        
        # Initialize from configuration
        self._initialize_from_config()
    
    def _initialize_from_config(self):
        """Initialize MCP service from configuration."""
        mcp_servers = self.config.get_mcp_servers()
        
        for name, config_server in mcp_servers.items():
            # Convert config to MCP server config
            server_config = MCPServerConfig(
                name=config_server.name,
                command=config_server.command,
                args=config_server.args,
                env=config_server.env,
                timeout=config_server.timeout,
                enabled=config_server.enabled,
                priority=config_server.priority,
                capabilities=config_server.capabilities
            )
            
            # Add to connection manager and registry
            self.connection_manager.add_server(server_config)
            self.server_registry.register_server(server_config)
            
            self.logger.info(f"Configured MCP server: {name}")
    
    async def start(self) -> bool:
        """Start the MCP service."""
        if self.is_running:
            self.logger.warning("MCP service already running")
            return True
        
        try:
            self.logger.info("Starting MCP service...")
            
            # Start connection manager
            await self.connection_manager.start()
            
            # Start health monitoring
            await self.health_monitor.start_monitoring()
            
            # Setup alert callbacks
            self.health_monitor.add_alert_callback(self._handle_health_alert)
            
            self.is_running = True
            self.startup_time = datetime.now()
            
            self.logger.info("MCP service started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP service: {e}")
            return False
    
    async def stop(self):
        """Stop the MCP service."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping MCP service...")
        
        # Stop health monitoring
        await self.health_monitor.stop_monitoring()
        
        # Stop connection manager
        await self.connection_manager.stop()
        
        self.is_running = False
        self.logger.info("MCP service stopped")
    
    async def query_server(self, request: str, 
                          preferred_server: Optional[str] = None,
                          required_capabilities: Optional[List[str]] = None,
                          context: Optional[Dict[str, Any]] = None) -> Any:
        """Query MCP servers with intelligent routing."""
        if not self.is_running:
            raise MCPError("MCP service not running")
        
        context = context or {}
        
        # Find best server if not specified
        if preferred_server:
            server_name = preferred_server
            if server_name not in self.connection_manager.get_available_servers():
                raise MCPError(f"Preferred server '{server_name}' not available")
        else:
            # Use registry to find best match
            match = self.server_registry.find_best_server(
                request, required_capabilities, context
            )
            if not match:
                raise MCPError("No suitable MCP server found for request")
            server_name = match.server_name
        
        try:
            start_time = datetime.now()
            
            # Send request to server using tools/call method
            result = await self.connection_manager.send_request(
                server_name, "tools/call", {
                    "name": request,
                    "arguments": context
                }
            )
            
            # Update performance metrics
            response_time = (datetime.now() - start_time).total_seconds()
            self.server_registry.update_performance(server_name, response_time, True)
            
            self.logger.debug(f"Successfully queried {server_name} in {response_time:.2f}s")
            return result
            
        except Exception as e:
            # Update performance metrics for failure
            response_time = (datetime.now() - start_time).total_seconds()
            self.server_registry.update_performance(server_name, response_time, False)
            
            self.logger.error(f"Failed to query {server_name}: {e}")
            
            # Try fallback server if available
            if not preferred_server:
                fallback_matches = self.server_registry.find_matches(
                    request, required_capabilities or [], context
                )
                
                # Filter out the failed server
                fallback_matches = [m for m in fallback_matches if m.server_name != server_name]
                
                if fallback_matches:
                    fallback_server = fallback_matches[0].server_name
                    self.logger.info(f"Trying fallback server: {fallback_server}")
                    return await self.query_server(
                        request, fallback_server, required_capabilities, context
                    )
            
            raise
    
    async def get_documentation(self, library: str, topic: Optional[str] = None) -> str:
        """Get documentation using Context7 or similar documentation server."""
        context = {
            "library": library,
            "topic": topic,
            "type": "documentation"
        }
        
        return await self.query_server(
            f"Get documentation for {library}" + (f" topic: {topic}" if topic else ""),
            required_capabilities=["documentation", "search"],
            context=context
        )
    
    async def analyze_code(self, code: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Analyze code using Sequential or analysis-capable server."""
        analysis_context = {
            "code": code,
            "context": context,
            "type": "analysis"
        }
        
        return await self.query_server(
            "Analyze this code for issues, improvements, and patterns",
            required_capabilities=["analysis", "reasoning"],
            context=analysis_context
        )
    
    async def generate_ui_component(self, description: str, 
                                   framework: str = "react") -> Dict[str, Any]:
        """Generate UI component using Magic or UI generation server."""
        ui_context = {
            "description": description,
            "framework": framework,
            "type": "ui_generation"
        }
        
        return await self.query_server(
            f"Generate {framework} component: {description}",
            required_capabilities=["generation", "ui"],
            context=ui_context
        )
    
    async def run_tests(self, test_type: str = "unit", 
                       target: Optional[str] = None) -> Dict[str, Any]:
        """Run tests using Playwright or testing server."""
        test_context = {
            "test_type": test_type,
            "target": target,
            "type": "testing"
        }
        
        return await self.query_server(
            f"Run {test_type} tests" + (f" for {target}" if target else ""),
            required_capabilities=["testing", "validation"],
            context=test_context
        )
    
    def get_available_servers(self) -> List[str]:
        """Get list of available MCP servers."""
        return self.connection_manager.get_available_servers()
    
    def get_server_capabilities(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """Get capabilities for specific server or all servers."""
        if server_name:
            return self.connection_manager.get_server_capabilities(server_name)
        else:
            return self.server_registry.get_capabilities_summary()
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive MCP service status."""
        health_summary = self.health_monitor.get_health_summary()
        registry_status = self.server_registry.get_server_status()
        
        return {
            "running": self.is_running,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "uptime": str(datetime.now() - self.startup_time) if self.startup_time else None,
            "connection_manager": {
                "available_servers": self.connection_manager.get_available_servers(),
                "total_servers": len(self.connection_manager.server_configs)
            },
            "health_monitor": health_summary,
            "server_registry": registry_status
        }
    
    def enable_server(self, server_name: str) -> bool:
        """Enable an MCP server with validation."""
        try:
            # Use the enhanced config validation
            success = self.config.enable_mcp_server(server_name)
            
            if success and server_name in self.connection_manager.server_configs:
                config = self.connection_manager.server_configs[server_name]
                config.enabled = True
                
                # Restart connection if service is running
                if self.is_running:
                    asyncio.create_task(self.connection_manager.connect_server(server_name))
                
                self.logger.info(f"Enabled MCP server: {server_name}")
                return True
                
        except ValueError as e:
            self.logger.error(f"Failed to enable MCP server {server_name}: {e}")
            return False
            
        return False
    
    def disable_server(self, server_name: str) -> bool:
        """Disable an MCP server."""
        success = self.config.disable_mcp_server(server_name)
        
        if success and server_name in self.connection_manager.server_configs:
            config = self.connection_manager.server_configs[server_name]
            config.enabled = False
            
            # Disconnect if service is running
            if self.is_running:
                asyncio.create_task(self.connection_manager.disconnect_server(server_name))
            
            self.logger.info(f"Disabled MCP server: {server_name}")
            return True
        return success
    
    def add_custom_server(self, name: str, command: List[str], 
                         capabilities: Optional[List[str]] = None,
                         **kwargs) -> bool:
        """Add a custom MCP server configuration."""
        try:
            server_config = MCPServerConfig(
                name=name,
                command=command,
                capabilities=capabilities or [],
                **kwargs
            )
            
            # Add to connection manager and registry
            self.connection_manager.add_server(server_config)
            self.server_registry.register_server(server_config)
            
            # Update configuration
            self.config.user_config.setdefault("mcp_servers", {})[name] = {
                "command": command,
                "capabilities": capabilities or [],
                "enabled": kwargs.get("enabled", True),
                **kwargs
            }
            
            self.logger.info(f"Added custom MCP server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add custom server {name}: {e}")
            return False
    
    def diagnose_routing(self, request: str) -> Dict[str, Any]:
        """Diagnose MCP server routing for a request."""
        return self.server_registry.diagnose_routing(request)
    
    def _handle_health_alert(self, server_name: str, status: HealthStatus, message: str):
        """Handle health alerts from the monitoring system."""
        self.logger.warning(f"Health alert for {server_name}: {status.value} - {message}")
        
        if status == HealthStatus.CRITICAL or status == HealthStatus.DOWN:
            # Could trigger additional recovery actions here
            self.logger.error(f"Server {server_name} is in critical state")
    
    async def restart_server(self, server_name: str) -> bool:
        """Restart a specific MCP server."""
        try:
            # Disconnect first
            await self.connection_manager.disconnect_server(server_name)
            
            # Wait a moment
            await asyncio.sleep(1.0)
            
            # Reconnect
            success = await self.connection_manager.connect_server(server_name)
            
            if success:
                self.logger.info(f"Successfully restarted server: {server_name}")
            else:
                self.logger.error(f"Failed to restart server: {server_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error restarting server {server_name}: {e}")
            return False