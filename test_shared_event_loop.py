#!/usr/bin/env python3
"""
Test script for SharedEventLoopAgent implementation.
Tests the architecture components and basic functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add codexa to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.shared_event_loop_agent import SharedEventLoopAgent
from codexa.enhanced_config import EnhancedConfig


async def test_agent_initialization():
    """Test agent initialization with all components."""
    print("🧪 Testing agent initialization...")
    
    # Set a dummy API key for testing
    os.environ["ANTHROPIC_API_KEY"] = "sk-test-key-for-testing"
    
    try:
        config = EnhancedConfig()
        agent = SharedEventLoopAgent(config)
        
        # Test component initialization
        status = agent.get_agent_status()
        print(f"✅ Agent Status: {status}")
        
        # Test tool registry
        tools = agent.tool_registry.get_all_tools()
        print(f"✅ Tools registered: {len(tools)}")
        
        # Test session management
        session_id = await agent.start_chat_session()
        session_info = agent.get_session_info()
        print(f"✅ Session created: {session_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False


async def test_conversation_flow():
    """Test basic conversation flow without actual API calls."""
    print("\n🧪 Testing conversation flow...")
    
    try:
        config = EnhancedConfig()
        agent = SharedEventLoopAgent(config)
        
        # Start session
        await agent.start_chat_session()
        
        # Test conversation methods
        await agent._add_to_conversation("Hello, test message")
        
        session_info = agent.get_session_info()
        print(f"✅ Message added to conversation: {session_info['message_count']} messages")
        
        # Test tool context creation
        tool_context = agent._create_tool_context({"request": "test"})
        print(f"✅ Tool context created: {tool_context.request_id}")
        
        # Test Anthropic tool format
        anthropic_tools = agent._get_anthropic_tools()
        print(f"✅ Anthropic tools formatted: {len(anthropic_tools)} tools")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversation flow test failed: {e}")
        return False


async def test_tool_execution_loop():
    """Test tool execution loop structure."""
    print("\n🧪 Testing tool execution loop...")
    
    try:
        config = EnhancedConfig()
        agent = SharedEventLoopAgent(config)
        
        # Mock tool call object
        class MockToolCall:
            def __init__(self):
                self.name = "test_tool"
                self.input = {"request": "test"}
                self.id = "test_id"
        
        # Test tool execution loop structure
        mock_call = MockToolCall()
        
        # This will fail because the tool doesn't exist, but tests the loop structure
        result = await agent._tool_execution_loop(mock_call)
        
        print(f"✅ Tool execution loop executed: {result}")
        assert result["tool_use_id"] == "test_id"
        assert result["is_error"] == True  # Expected for non-existent tool
        
        return True
        
    except Exception as e:
        print(f"❌ Tool execution loop test failed: {e}")
        return False


async def test_component_architecture():
    """Test that all architectural components are properly implemented."""
    print("\n🧪 Testing component architecture...")
    
    try:
        config = EnhancedConfig()
        agent = SharedEventLoopAgent(config)
        
        # Test Agent -> Anthropic Client
        assert hasattr(agent, 'anthropic_client'), "Missing Anthropic Client component"
        print("✅ Agent -> Anthropic Client: Connected")
        
        # Test Agent -> Tool Registry  
        assert hasattr(agent, 'tool_registry'), "Missing Tool Registry component"
        print("✅ Agent -> Tool Registry: Connected")
        
        # Test Agent -> getUserMessage Function
        assert hasattr(agent, 'get_user_message'), "Missing getUserMessage function"
        print("✅ Agent -> getUserMessage Function: Connected")
        
        # Test Agent -> Verbose Logging
        assert hasattr(agent, 'logger'), "Missing Verbose Logging component"
        print("✅ Agent -> Verbose Logging: Connected")
        
        # Test event loop components
        assert hasattr(agent, '_add_to_conversation'), "Missing conversation management"
        assert hasattr(agent, '_run_inference'), "Missing inference capability"
        assert hasattr(agent, '_execute_tools'), "Missing tool execution"
        assert hasattr(agent, '_tool_execution_loop'), "Missing tool execution loop"
        print("✅ Event Loop Components: All present")
        
        return True
        
    except Exception as e:
        print(f"❌ Component architecture test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting SharedEventLoopAgent Tests\n")
    
    tests = [
        test_agent_initialization,
        test_conversation_flow,
        test_tool_execution_loop,
        test_component_architecture
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! SharedEventLoopAgent is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)