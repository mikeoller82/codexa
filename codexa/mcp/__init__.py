"""
MCP (Model Context Protocol) integration for Codexa.

This module provides MCP server connection management, protocol handling,
and intelligent routing for enhanced AI capabilities.
"""

from .connection_manager import MCPConnectionManager
from .protocol import MCPProtocol, MCPMessage, MCPError
from .server_registry import MCPServerRegistry
from .health_monitor import MCPHealthMonitor
from .serena_client import SerenaClient, SerenaManager, SerenaProjectConfig

__all__ = [
    "MCPConnectionManager",
    "MCPProtocol", 
    "MCPMessage",
    "MCPError",
    "MCPServerRegistry",
    "MCPHealthMonitor",
    "SerenaClient",
    "SerenaManager", 
    "SerenaProjectConfig"
]