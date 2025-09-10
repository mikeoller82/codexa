"""
Serena MCP server client with semantic code analysis capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import json

from .connection_manager import MCPConnection, MCPServerConfig, ConnectionState
from .protocol import MCPProtocol, MCPMessage, MCPError


@dataclass
class SerenaProjectConfig:
    """Configuration for Serena project activation."""
    path: str
    name: Optional[str] = None
    auto_index: bool = True
    context_mode: str = "ide-assistant"
    modes: List[str] = field(default_factory=lambda: ["interactive"])
    

@dataclass
class SerenaToolCall:
    """Serena tool call parameters."""
    tool_name: str
    parameters: Dict[str, Any]
    timeout: Optional[float] = None


class SerenaClient:
    """Specialized client for Serena MCP server with semantic code operations."""
    
    def __init__(self, config: MCPServerConfig):
        """Initialize Serena client."""
        self.config = config
        self.connection = MCPConnection(config)
        self.logger = logging.getLogger(f"serena.{config.name}")
        
        # Serena-specific state
        self.active_project: Optional[SerenaProjectConfig] = None
        self.available_tools: Dict[str, Dict[str, Any]] = {}
        self.project_capabilities: Dict[str, Any] = {}
        self.onboarding_completed: bool = False
        
        # Tool categories for intelligent routing
        self.semantic_tools = {
            "find_symbol", "get_symbols_overview", "find_referencing_symbols",
            "replace_symbol_body", "insert_after_symbol", "insert_before_symbol"
        }
        
        self.file_tools = {
            "read_file", "create_text_file", "search_for_pattern", "replace_regex"
        }
        
        self.project_tools = {
            "activate_project", "onboarding", "list_dir", "find_file"
        }
        
        self.execution_tools = {
            "execute_shell_command"
        }
        
        self.memory_tools = {
            "write_memory", "read_memory", "list_memories", "delete_memory"
        }
    
    async def connect(self) -> bool:
        """Connect to Serena MCP server."""
        success = await self.connection.connect()
        
        if success:
            # Discover available tools
            await self._discover_tools()
            self.logger.info(f"Serena client connected with {len(self.available_tools)} tools")
        
        return success
    
    async def disconnect(self):
        """Disconnect from Serena server."""
        await self.connection.disconnect()
        self.active_project = None
        self.available_tools.clear()
        self.project_capabilities.clear()
        self.onboarding_completed = False
    
    async def activate_project(self, project_config: SerenaProjectConfig) -> bool:
        """Activate a project in Serena for semantic operations."""
        try:
            # Call activate_project tool
            result = await self.call_tool("activate_project", {
                "project_path": project_config.path
            })
            
            if result.get("success", False):
                self.active_project = project_config
                self.logger.info(f"Activated Serena project: {project_config.path}")
                
                # Check if onboarding has been performed
                onboarding_result = await self.call_tool("check_onboarding_performed", {})
                self.onboarding_completed = onboarding_result.get("performed", False)
                
                # Auto-index if requested and not done
                if project_config.auto_index and not self.onboarding_completed:
                    await self.perform_onboarding()
                
                return True
            else:
                self.logger.error(f"Failed to activate project: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error activating project: {e}")
            return False
    
    async def perform_onboarding(self) -> bool:
        """Perform Serena project onboarding."""
        try:
            result = await self.call_tool("onboarding", {})
            
            if result.get("success", False):
                self.onboarding_completed = True
                self.logger.info("Serena project onboarding completed")
                return True
            else:
                self.logger.error(f"Onboarding failed: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during onboarding: {e}")
            return False
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], 
                       timeout: Optional[float] = None) -> Any:
        """Call a Serena tool with parameters."""
        if tool_name not in self.available_tools:
            raise MCPError(f"Tool not available: {tool_name}")
        
        try:
            # Prepare tool call request
            params = {
                "name": tool_name,
                "arguments": parameters
            }
            
            # Set timeout if specified
            original_timeout = self.connection.config.timeout
            if timeout:
                self.connection.config.timeout = int(timeout)
            
            try:
                result = await self.connection.send_request("tools/call", params)
                
                # Parse tool result
                if isinstance(result, dict):
                    if "content" in result:
                        # Extract content from MCP tool response
                        content = result["content"]
                        if isinstance(content, list) and len(content) > 0:
                            # Return first content item data
                            return content[0].get("text", content[0])
                        return content
                    return result
                
                return result
                
            finally:
                # Restore original timeout
                self.connection.config.timeout = original_timeout
                
        except Exception as e:
            self.logger.error(f"Tool call failed {tool_name}: {e}")
            raise MCPError(f"Serena tool call failed: {tool_name} - {e}")
    
    # Semantic Code Analysis Methods
    
    async def find_symbols(self, query: str, symbol_type: Optional[str] = None, 
                          local_only: bool = False) -> List[Dict[str, Any]]:
        """Find symbols matching a query."""
        params = {
            "query": query,
            "local": local_only
        }
        if symbol_type:
            params["type_filter"] = symbol_type
        
        return await self.call_tool("find_symbol", params)
    
    async def get_file_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        """Get overview of symbols defined in a file."""
        return await self.call_tool("get_symbols_overview", {"file_path": file_path})
    
    async def find_symbol_references(self, file_path: str, line: int, column: int,
                                   reference_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find symbols that reference the symbol at given location."""
        params = {
            "file_path": file_path,
            "line": line,
            "column": column
        }
        if reference_type:
            params["type_filter"] = reference_type
        
        return await self.call_tool("find_referencing_symbols", params)
    
    async def replace_symbol(self, file_path: str, line: int, column: int,
                           new_body: str) -> bool:
        """Replace the body of a symbol at given location."""
        params = {
            "file_path": file_path,
            "line": line,
            "column": column,
            "new_body": new_body
        }
        
        result = await self.call_tool("replace_symbol_body", params)
        return result.get("success", False)
    
    async def insert_after_symbol(self, file_path: str, line: int, column: int,
                                 content: str) -> bool:
        """Insert content after a symbol definition."""
        params = {
            "file_path": file_path,
            "line": line,
            "column": column,
            "content": content
        }
        
        result = await self.call_tool("insert_after_symbol", params)
        return result.get("success", False)
    
    async def insert_before_symbol(self, file_path: str, line: int, column: int,
                                  content: str) -> bool:
        """Insert content before a symbol definition."""
        params = {
            "file_path": file_path,
            "line": line,
            "column": column,
            "content": content
        }
        
        result = await self.call_tool("insert_before_symbol", params)
        return result.get("success", False)
    
    # File Operations
    
    async def read_file(self, file_path: str) -> str:
        """Read file contents."""
        result = await self.call_tool("read_file", {"file_path": file_path})
        return result.get("content", "")
    
    async def create_file(self, file_path: str, content: str) -> bool:
        """Create or overwrite a file."""
        params = {
            "file_path": file_path,
            "content": content
        }
        
        result = await self.call_tool("create_text_file", params)
        return result.get("success", False)
    
    async def search_pattern(self, pattern: str, include_files: Optional[List[str]] = None,
                           exclude_files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for a pattern in project files."""
        params = {"pattern": pattern}
        
        if include_files:
            params["include_files"] = include_files
        if exclude_files:
            params["exclude_files"] = exclude_files
        
        return await self.call_tool("search_for_pattern", params)
    
    async def replace_with_regex(self, file_path: str, pattern: str, 
                               replacement: str) -> bool:
        """Replace content in file using regular expressions."""
        params = {
            "file_path": file_path,
            "pattern": pattern,
            "replacement": replacement
        }
        
        result = await self.call_tool("replace_regex", params)
        return result.get("success", False)
    
    # Project Operations
    
    async def list_directory(self, path: str, recursive: bool = False) -> List[str]:
        """List files and directories."""
        params = {
            "path": path,
            "recursive": recursive
        }
        
        result = await self.call_tool("list_dir", params)
        return result.get("files", [])
    
    async def find_files(self, patterns: List[str], base_path: Optional[str] = None) -> List[str]:
        """Find files matching patterns."""
        params = {"patterns": patterns}
        
        if base_path:
            params["base_path"] = base_path
        
        result = await self.call_tool("find_file", params)
        return result.get("files", [])
    
    # Shell Execution
    
    async def execute_command(self, command: str, working_dir: Optional[str] = None,
                            timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute shell command."""
        params = {"command": command}
        
        if working_dir:
            params["working_directory"] = working_dir
        
        return await self.call_tool("execute_shell_command", params, timeout=timeout)
    
    # Memory Management
    
    async def write_memory(self, name: str, content: str) -> bool:
        """Write a memory for future reference."""
        params = {
            "name": name,
            "content": content
        }
        
        result = await self.call_tool("write_memory", params)
        return result.get("success", False)
    
    async def read_memory(self, name: str) -> Optional[str]:
        """Read a memory by name."""
        try:
            result = await self.call_tool("read_memory", {"name": name})
            return result.get("content")
        except MCPError:
            return None
    
    async def list_memories(self) -> List[str]:
        """List all available memories."""
        result = await self.call_tool("list_memories", {})
        return result.get("memories", [])
    
    async def delete_memory(self, name: str) -> bool:
        """Delete a memory."""
        result = await self.call_tool("delete_memory", {"name": name})
        return result.get("success", False)
    
    # Internal Methods
    
    async def _discover_tools(self):
        """Discover available tools from Serena server."""
        try:
            # Get tools list - MCP protocol requires explicit empty params
            result = await self.connection.send_request("tools/list", {})
            
            if isinstance(result, dict) and "tools" in result:
                tools = result["tools"]
                
                for tool in tools:
                    if isinstance(tool, dict) and "name" in tool:
                        tool_name = tool["name"]
                        self.available_tools[tool_name] = tool
                        
        except Exception as e:
            self.logger.error(f"Failed to discover tools: {e}")
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        return self.available_tools.get(tool_name)
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """Get tools by category."""
        category_map = {
            "semantic": self.semantic_tools,
            "file": self.file_tools,
            "project": self.project_tools,
            "execution": self.execution_tools,
            "memory": self.memory_tools
        }
        
        tools = category_map.get(category, set())
        return [tool for tool in tools if tool in self.available_tools]
    
    def is_project_active(self) -> bool:
        """Check if a project is currently active."""
        return self.active_project is not None
    
    def is_connected(self) -> bool:
        """Check if client is connected to Serena server."""
        return self.connection.state == ConnectionState.CONNECTED
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get current capabilities."""
        return {
            "connected": self.is_connected(),
            "project_active": self.is_project_active(),
            "onboarding_completed": self.onboarding_completed,
            "available_tools": list(self.available_tools.keys()),
            "tool_categories": {
                "semantic": len(self.get_tools_by_category("semantic")),
                "file": len(self.get_tools_by_category("file")),
                "project": len(self.get_tools_by_category("project")),
                "execution": len(self.get_tools_by_category("execution")),
                "memory": len(self.get_tools_by_category("memory"))
            }
        }


class SerenaManager:
    """Manager for multiple Serena client connections."""
    
    def __init__(self):
        """Initialize Serena manager."""
        self.clients: Dict[str, SerenaClient] = {}
        self.default_client: Optional[SerenaClient] = None
        self.logger = logging.getLogger("serena.manager")
    
    def add_client(self, name: str, config: MCPServerConfig) -> SerenaClient:
        """Add a Serena client."""
        client = SerenaClient(config)
        self.clients[name] = client
        
        # Set as default if first client
        if not self.default_client:
            self.default_client = client
        
        self.logger.info(f"Added Serena client: {name}")
        return client
    
    def remove_client(self, name: str):
        """Remove a Serena client."""
        if name in self.clients:
            client = self.clients[name]
            asyncio.create_task(client.disconnect())
            del self.clients[name]
            
            # Update default client
            if self.default_client == client:
                self.default_client = next(iter(self.clients.values()), None)
            
            self.logger.info(f"Removed Serena client: {name}")
    
    async def connect_all(self):
        """Connect all Serena clients."""
        for name, client in self.clients.items():
            try:
                await client.connect()
            except Exception as e:
                self.logger.error(f"Failed to connect Serena client {name}: {e}")
    
    async def disconnect_all(self):
        """Disconnect all Serena clients."""
        for client in self.clients.values():
            await client.disconnect()
    
    def get_client(self, name: Optional[str] = None) -> Optional[SerenaClient]:
        """Get a Serena client by name or default."""
        if name:
            return self.clients.get(name)
        return self.default_client
    
    def get_available_clients(self) -> List[str]:
        """Get list of available (connected) clients."""
        return [
            name for name, client in self.clients.items()
            if client.is_connected()
        ]