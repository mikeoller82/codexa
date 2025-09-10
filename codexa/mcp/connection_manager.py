"""
MCP server connection manager with health monitoring and automatic reconnection.
"""

import asyncio
import subprocess
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .protocol import MCPProtocol, MCPMessage, MCPError


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"  
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str
    command: List[str]
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    enabled: bool = True
    priority: int = 1  # Higher priority = preferred server
    capabilities: List[str] = field(default_factory=list)  # Expected capabilities


@dataclass
class ConnectionMetrics:
    """Connection performance metrics."""
    connection_time: Optional[datetime] = None
    last_request_time: Optional[datetime] = None
    total_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    uptime: timedelta = timedelta()


class MCPConnection:
    """Individual MCP server connection."""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self.process: Optional[subprocess.Popen] = None
        self.metrics = ConnectionMetrics()
        self.capabilities: Dict[str, Any] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.retry_count = 0
        self.last_error: Optional[str] = None
        
        # Logging
        self.logger = logging.getLogger(f"mcp.{config.name}")
        
        # Message reading task
        self._read_task = None
    
    async def connect(self) -> bool:
        """Establish connection to MCP server."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return True
            
        self.state = ConnectionState.CONNECTING
        self.logger.info(f"Connecting to MCP server: {self.config.name}")
        
        try:
            # Start server process
            full_command = self.config.command + (self.config.args or [])
            
            # Prepare environment - inherit current env and add custom vars
            import os
            env = os.environ.copy()
            if self.config.env:
                env.update(self.config.env)
            
            # Ensure common bin directories are in PATH
            current_path = env.get('PATH', '')
            home_dir = os.path.expanduser('~')
            additional_paths = [
                os.path.join(home_dir, '.local', 'bin'),
                os.path.join(home_dir, '.cargo', 'bin'),
                '/usr/local/bin'
            ]
            
            for path in additional_paths:
                if os.path.exists(path) and path not in current_path:
                    if current_path:
                        env['PATH'] = f"{path}:{current_path}"
                    else:
                        env['PATH'] = path
                    current_path = env['PATH']
            
            self.process = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Start message reading loop
            self._read_task = asyncio.create_task(self._message_read_loop())
            
            # Initialize MCP protocol
            if await self._initialize():
                self.state = ConnectionState.CONNECTED
                self.metrics.connection_time = datetime.now()
                self.retry_count = 0
                self.last_error = None
                self.logger.info(f"Successfully connected to {self.config.name}")
                return True
            else:
                await self._cleanup()
                self.state = ConnectionState.ERROR
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.config.name}: {e}")
            self.last_error = str(e)
            self.state = ConnectionState.ERROR
            await self._cleanup()
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        self.logger.info(f"Disconnecting from {self.config.name}")
        self.state = ConnectionState.DISCONNECTED
        await self._cleanup()
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send request to MCP server."""
        if self.state != ConnectionState.CONNECTED:
            raise MCPError(f"Server {self.config.name} not connected", MCPProtocol.SERVER_UNAVAILABLE)

        # Handle None params (no parameters) vs empty dict
        if params is None:
            request = MCPProtocol.create_request(method, None)
        else:
            request = MCPProtocol.create_request(method, params)

        try:
            start_time = datetime.now()

            # Send request
            await self._write_message(request)

            # Create future for response
            future = asyncio.Future()
            self.pending_requests[request.id] = future

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(future, timeout=self.config.timeout)

                # Update metrics
                response_time = (datetime.now() - start_time).total_seconds()
                self.metrics.total_requests += 1
                self.metrics.last_request_time = datetime.now()
                self._update_average_response_time(response_time)

                # Return the result from the MCPMessage, handling errors
                if response.error:
                    error_code = response.error.get("code", -1)
                    error_message = response.error.get("message", "Unknown error")

                    # Provide more specific error messages for common MCP errors
                    if error_code == -32602:  # INVALID_PARAMS
                        raise MCPError(f"Invalid parameters for {method}: {error_message}", error_code)
                    elif error_code == -32601:  # METHOD_NOT_FOUND
                        raise MCPError(f"Method {method} not found on server {self.config.name}", error_code)
                    elif error_code == -32600:  # INVALID_REQUEST
                        raise MCPError(f"Invalid request to server {self.config.name}: {error_message}", error_code)
                    else:
                        raise MCPError(f"Server error: {error_message}", error_code)

                return response.result

            except asyncio.TimeoutError:
                self.metrics.failed_requests += 1
                raise MCPError(f"Request timeout for {self.config.name}", MCPProtocol.TIMEOUT_ERROR)
            finally:
                self.pending_requests.pop(request.id, None)

        except Exception as e:
            self.metrics.failed_requests += 1
            self.logger.error(f"Request failed for {self.config.name}: {e}")
            raise
    
    async def _initialize(self) -> bool:
        """Initialize MCP protocol handshake."""
        try:
            # Send initialize request
            client_info = {
                "name": "codexa",
                "version": "1.0.1"
            }
            
            init_request = MCPProtocol.create_initialize_request(client_info)
            await self._write_message(init_request)
            
            # Wait for initialize response
            response = await self._read_message()
            if not response or response.error:
                self.logger.error(f"Initialize failed: {response.error if response else 'No response'}")
                return False
            
            # Parse capabilities
            if response.result and "capabilities" in response.result:
                self.capabilities = MCPProtocol.parse_capabilities(response.result["capabilities"])
                self.logger.info(f"Server capabilities: {list(self.capabilities.keys())}")
            
            # Send initialized notification
            initialized = MCPProtocol.create_initialized_notification()
            await self._write_message(initialized)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
    
    async def _write_message(self, message: MCPMessage):
        """Write message to server process."""
        if not self.process or not self.process.stdin:
            raise MCPError("Process not available")
        
        json_str = message.to_json()
        self.process.stdin.write(json_str + "\n")
        self.process.stdin.flush()
    
    async def _read_message(self) -> Optional[MCPMessage]:
        """Read message from server process."""
        if not self.process or not self.process.stdout:
            return None
        
        try:
            line = self.process.stdout.readline()
            if not line:
                return None
            
            return MCPMessage.from_json(line.strip())
        except Exception as e:
            self.logger.error(f"Failed to read message: {e}")
            return None
    
    async def _message_read_loop(self):
        """Async message reading loop to handle responses from the server."""
        try:
            while self.process and self.process.poll() is None:
                try:
                    # Use asyncio to read from stdout without blocking
                    loop = asyncio.get_event_loop()
                    line = await loop.run_in_executor(None, self.process.stdout.readline)
                    
                    if not line:
                        break
                        
                    message = MCPMessage.from_json(line.strip())
                    if message and hasattr(message, 'id') and message.id in self.pending_requests:
                        # Complete the pending request
                        future = self.pending_requests.pop(message.id)
                        if not future.done():
                            future.set_result(message)
                    
                except Exception as e:
                    self.logger.error(f"Error in message read loop: {e}")
                    break
                    
        except asyncio.CancelledError:
            pass  # Task cancelled, exit gracefully
        except Exception as e:
            self.logger.error(f"Message read loop failed: {e}")
            self.state = ConnectionState.ERROR
    
    def _update_average_response_time(self, response_time: float):
        """Update average response time metric."""
        total = self.metrics.total_requests
        current_avg = self.metrics.average_response_time
        self.metrics.average_response_time = ((current_avg * (total - 1)) + response_time) / total
    
    async def _cleanup(self):
        """Clean up connection resources."""
        # Cancel read task
        if hasattr(self, '_read_task') and self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None
        
        # Cancel pending requests
        for future in self.pending_requests.values():
            if not future.done():
                future.cancel()
        self.pending_requests.clear()
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        if self.state != ConnectionState.CONNECTED:
            return False
        
        # Check if process is still running
        if not self.process or self.process.poll() is not None:
            return False
        
        # Check error rate
        if self.metrics.total_requests > 0:
            error_rate = self.metrics.failed_requests / self.metrics.total_requests
            if error_rate > 0.5:  # 50% error rate threshold
                return False
        
        return True


class MCPConnectionManager:
    """Manager for multiple MCP server connections."""
    
    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.logger = logging.getLogger("mcp.manager")
        self.health_check_interval = 30  # seconds
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
    
    def add_server(self, config: MCPServerConfig):
        """Add MCP server configuration."""
        self.server_configs[config.name] = config
        self.logger.info(f"Added MCP server config: {config.name}")
    
    def remove_server(self, name: str):
        """Remove MCP server configuration."""
        if name in self.server_configs:
            del self.server_configs[name]
        if name in self.connections:
            asyncio.create_task(self.connections[name].disconnect())
            del self.connections[name]
        self.logger.info(f"Removed MCP server: {name}")
    
    async def start(self):
        """Start connection manager and connect to all servers."""
        self._running = True
        self.logger.info("Starting MCP connection manager")
        
        # Connect to all enabled servers
        for config in self.server_configs.values():
            if config.enabled:
                await self.connect_server(config.name)
        
        # Start health monitoring
        self._health_task = asyncio.create_task(self._health_monitor_loop())
    
    async def stop(self):
        """Stop connection manager and disconnect all servers."""
        self._running = False
        self.logger.info("Stopping MCP connection manager")
        
        # Stop health monitoring
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all servers
        for connection in self.connections.values():
            await connection.disconnect()
        
        self.connections.clear()
    
    async def connect_server(self, name: str) -> bool:
        """Connect to specific MCP server."""
        if name not in self.server_configs:
            self.logger.error(f"No configuration found for server: {name}")
            return False
        
        config = self.server_configs[name]
        if not config.enabled:
            self.logger.info(f"Server {name} is disabled")
            return False
        
        # Create new connection if needed
        if name not in self.connections:
            self.connections[name] = MCPConnection(config)
        
        connection = self.connections[name]
        return await connection.connect()
    
    async def disconnect_server(self, name: str):
        """Disconnect from specific MCP server."""
        if name in self.connections:
            await self.connections[name].disconnect()
    
    async def send_request(self, server_name: str, method: str, 
                          params: Optional[Dict[str, Any]] = None) -> Any:
        """Send request to specific MCP server."""
        if server_name not in self.connections:
            raise MCPError(f"Server {server_name} not connected", MCPProtocol.SERVER_UNAVAILABLE)
        
        connection = self.connections[server_name]
        return await connection.send_request(method, params)
    
    def get_available_servers(self) -> List[str]:
        """Get list of available (connected) servers."""
        return [
            name for name, conn in self.connections.items() 
            if conn.state == ConnectionState.CONNECTED
        ]
    
    def get_server_capabilities(self, server_name: str) -> Dict[str, Any]:
        """Get capabilities for specific server."""
        if server_name in self.connections:
            return self.connections[server_name].capabilities
        return {}
    
    def get_server_metrics(self, server_name: str) -> Optional[ConnectionMetrics]:
        """Get performance metrics for specific server."""
        if server_name in self.connections:
            return self.connections[server_name].metrics
        return None
    
    def get_all_metrics(self) -> Dict[str, ConnectionMetrics]:
        """Get metrics for all servers."""
        return {
            name: conn.metrics 
            for name, conn in self.connections.items()
        }
    
    async def _health_monitor_loop(self):
        """Health monitoring loop."""
        while self._running:
            try:
                await self._check_server_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _check_server_health(self):
        """Check health of all servers and reconnect if needed."""
        for name, connection in list(self.connections.items()):
            if not connection.is_healthy and connection.config.enabled:
                self.logger.warning(f"Server {name} is unhealthy, attempting reconnection")
                
                # Attempt reconnection with retry logic
                if connection.retry_count < connection.config.max_retries:
                    connection.retry_count += 1
                    connection.state = ConnectionState.RECONNECTING
                    
                    await asyncio.sleep(connection.config.retry_delay)
                    success = await connection.connect()
                    
                    if success:
                        self.logger.info(f"Successfully reconnected to {name}")
                    else:
                        self.logger.error(f"Failed to reconnect to {name} (attempt {connection.retry_count})")
                else:
                    self.logger.error(f"Max retries exceeded for {name}, marking as failed")
                    connection.state = ConnectionState.ERROR