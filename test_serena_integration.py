#!/usr/bin/env python3
"""
Test script for Serena MCP server integration with Codexa.
"""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_serena_integration():
    """Test Serena integration components."""
    print("🚀 Testing Serena MCP Server Integration")
    
    try:
        # Test 1: Import all Serena components
        print("\n📦 Testing imports...")
        
        from codexa.mcp.serena_client import SerenaClient, SerenaManager, SerenaProjectConfig
        from codexa.tools.serena import (
            BaseSerenaTool, CodeAnalysisTool, SymbolSearchTool, ReferenceSearchTool,
            SerenaFileOperationsTool, PatternSearchTool, ProjectManagementTool,
            MemoryManagementTool, ShellExecutionTool
        )
        from codexa.enhanced_config import EnhancedConfig
        from codexa.mcp_service import MCPService
        
        print("✅ All imports successful")
        
        # Test 2: Configuration
        print("\n⚙️ Testing configuration...")
        
        config = EnhancedConfig()
        mcp_servers = config.get_mcp_servers()
        
        if "serena" in mcp_servers:
            serena_config = mcp_servers["serena"]
            print(f"✅ Serena configuration found")
            print(f"   Command: {serena_config.command}")
            print(f"   Args: {serena_config.args}")
            print(f"   Enabled: {serena_config.enabled}")
            print(f"   Capabilities: {len(serena_config.capabilities)}")
        else:
            print("⚠️  Serena not found in configuration")
        
        # Test 3: MCP Service
        print("\n🔌 Testing MCP Service...")
        
        mcp_service = MCPService(config)
        
        # Check if Serena manager is initialized
        if hasattr(mcp_service, 'serena_manager'):
            print("✅ Serena manager initialized")
            available_clients = mcp_service.serena_manager.get_available_clients()
            print(f"   Available Serena clients: {available_clients}")
        else:
            print("❌ Serena manager not found in MCP service")
        
        # Test 4: Tool instantiation
        print("\n🛠️ Testing tool instantiation...")
        
        tools_to_test = [
            CodeAnalysisTool,
            SymbolSearchTool, 
            ReferenceSearchTool,
            SerenaFileOperationsTool,
            PatternSearchTool,
            ProjectManagementTool,
            MemoryManagementTool,
            ShellExecutionTool
        ]
        
        for tool_class in tools_to_test:
            try:
                tool = tool_class()
                print(f"✅ {tool.name}: {tool.description}")
                print(f"   Category: {tool.category}")
                print(f"   Capabilities: {len(tool.capabilities)}")
                print(f"   Serena tools: {tool.serena_tool_names}")
            except Exception as e:
                print(f"❌ {tool_class.__name__}: {e}")
        
        # Test 5: Client instantiation
        print("\n🔗 Testing client instantiation...")
        
        from codexa.mcp.connection_manager import MCPServerConfig
        
        test_config = MCPServerConfig(
            name="serena_test",
            command=["echo", "test"],
            enabled=True,
            capabilities=["semantic-analysis"]
        )
        
        try:
            client = SerenaClient(test_config)
            print("✅ Serena client created successfully")
            print(f"   Capabilities: {client.get_capabilities()}")
        except Exception as e:
            print(f"❌ Serena client creation failed: {e}")
        
        # Test 6: Project config
        print("\n📁 Testing project configuration...")
        
        try:
            project_config = SerenaProjectConfig(
                path="/tmp/test_project",
                name="test",
                auto_index=True,
                context_mode="ide-assistant"
            )
            print("✅ Project config created successfully")
            print(f"   Path: {project_config.path}")
            print(f"   Context mode: {project_config.context_mode}")
            print(f"   Auto index: {project_config.auto_index}")
        except Exception as e:
            print(f"❌ Project config creation failed: {e}")
        
        print("\n🎉 Integration test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tool_discovery():
    """Test if tools are discoverable by the tool registry."""
    print("\n🔍 Testing tool discovery...")
    
    try:
        from codexa.tools.base.tool_registry import ToolRegistry
        
        registry = ToolRegistry()
        discovered_count = registry.discover_tools("codexa.tools.serena")
        
        print(f"✅ Discovered {discovered_count} Serena tools")
        
        # Get all tools and filter for Serena
        all_tools = registry.get_all_tools()
        serena_tools = {name: info for name, info in all_tools.items() 
                       if info.category == "serena"}
        
        print(f"   Serena tools in registry: {len(serena_tools)}")
        for name, info in serena_tools.items():
            print(f"   - {name}: {info.description}")
        
        return len(serena_tools) > 0
        
    except Exception as e:
        print(f"❌ Tool discovery failed: {e}")
        return False

async def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 Serena MCP Integration Test Suite")
    print("=" * 60)
    
    # Run integration test
    integration_success = await test_serena_integration()
    
    # Run tool discovery test
    discovery_success = await test_tool_discovery()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Integration Test: {'✅ PASS' if integration_success else '❌ FAIL'}")
    print(f"Tool Discovery:   {'✅ PASS' if discovery_success else '❌ FAIL'}")
    
    overall_success = integration_success and discovery_success
    print(f"\nOverall Result:   {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Serena integration is ready to use!")
        print("\nTo enable Serena, add this to your ~/.codexarc:")
        print("""
mcp_servers:
  serena:
    enabled: true
    command: ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"]
    args: ["--context", "ide-assistant"]
    timeout: 30
        """)
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return overall_success

if __name__ == "__main__":
    asyncio.run(main())