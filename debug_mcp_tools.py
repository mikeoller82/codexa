#!/usr/bin/env python3
"""
Debug script to discover actual MCP tool names and formats.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from codexa.enhanced_config import EnhancedConfig
from codexa.mcp_service import MCPService

logging.basicConfig(level=logging.INFO)

async def discover_tools():
    """Discover actual tool names from MCP servers."""
    config = EnhancedConfig()
    mcp_service = MCPService(config)
    
    try:
        # Start service
        success = await mcp_service.start()
        if not success:
            print("Failed to start MCP service")
            return
        
        print("MCP Service started successfully\n")
        
        # Check available servers
        servers = mcp_service.get_available_servers()
        print(f"Available servers: {servers}\n")
        
        # Get capabilities for each server
        for server in servers:
            print(f"=== {server.upper()} SERVER ===")
            try:
                capabilities = mcp_service.get_server_capabilities(server)
                print(f"Capabilities: {capabilities}")
                
                # Try to get tools list
                if "tools" in capabilities:
                    tools = capabilities["tools"]
                    print(f"Available tools: {[tool.get('name', 'unknown') for tool in tools]}")
                    
                    # Print tool details
                    for tool in tools[:5]:  # First 5 tools
                        name = tool.get('name', 'unknown')
                        description = tool.get('description', 'No description')
                        print(f"  - {name}: {description}")
                
                print()
                
            except Exception as e:
                print(f"Error getting capabilities for {server}: {e}\n")
        
        # Test basic tool calls
        print("=== TESTING BASIC TOOL CALLS ===")
        
        # Try filesystem list tools call
        try:
            result = await mcp_service.connection_manager.send_request("filesystem", "tools/list")
            print(f"Filesystem tools/list result: {result}")
        except Exception as e:
            print(f"Filesystem tools/list error: {e}")
        
        # Try serena list tools call
        try:
            result = await mcp_service.connection_manager.send_request("serena", "tools/list")
            print(f"Serena tools/list result: {result}")
        except Exception as e:
            print(f"Serena tools/list error: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await mcp_service.stop()

if __name__ == "__main__":
    asyncio.run(discover_tools())