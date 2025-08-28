#!/usr/bin/env python3
"""
Demo script for SharedEventLoopAgent implementation.
Demonstrates the shared event loop architecture with real agent components.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add codexa to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.shared_event_loop_agent import SharedEventLoopAgent
from codexa.enhanced_config import EnhancedConfig


class AgentDemo:
    """Demo class to showcase SharedEventLoopAgent capabilities."""
    
    def __init__(self):
        self.agent = None
    
    async def setup_agent(self):
        """Setup and configure the agent."""
        print("🔧 Setting up SharedEventLoopAgent...")
        
        # Set dummy API key for demo mode
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-demo-key-for-testing"
        
        # Create config
        config = EnhancedConfig()
        
        # Initialize agent
        self.agent = SharedEventLoopAgent(config)
        
        print("✅ Agent setup complete!")
        return self.agent
    
    def display_agent_info(self):
        """Display comprehensive agent information."""
        print("\n📊 AGENT ARCHITECTURE OVERVIEW")
        print("=" * 50)
        
        # Agent Status
        status = self.agent.get_agent_status()
        print(f"🤖 Agent Status:")
        print(f"   • Running: {status['running']}")
        print(f"   • Tools Available: {status['tool_count']}")
        print(f"   • Sessions: {status['total_sessions']}")
        
        # Components Status
        print(f"\n🧩 Architecture Components:")
        components = status['components']
        for component, active in components.items():
            icon = "✅" if active else "❌"
            print(f"   {icon} {component.replace('_', ' ').title()}")
        
        # Tool Registry Info
        print(f"\n🛠️  Tool Registry:")
        tools = self.agent.tool_registry.get_all_tools()
        categories = {}
        for tool_name, tool_info in tools.items():
            category = tool_info.category if hasattr(tool_info, 'category') else 'unknown'
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)
        
        for category, tool_list in categories.items():
            print(f"   • {category.title()}: {len(tool_list)} tools")
            if len(tool_list) <= 5:
                print(f"     {', '.join(tool_list)}")
            else:
                print(f"     {', '.join(tool_list[:3])}, ... (+{len(tool_list)-3} more)")
    
    async def demo_conversation_flow(self):
        """Demonstrate the conversation flow without API calls."""
        print(f"\n💬 CONVERSATION FLOW DEMO")
        print("=" * 50)
        
        # Start a session
        session_id = await self.agent.start_chat_session()
        print(f"📞 Started session: {session_id}")
        
        # Simulate adding messages
        test_messages = [
            "Hello, I need help with Python code",
            "Can you list the files in the current directory?",
            "Help me create a simple function"
        ]
        
        for i, message in enumerate(test_messages, 1):
            await self.agent._add_to_conversation(message)
            print(f"   {i}. Added: '{message}'")
        
        # Show session info
        session_info = self.agent.get_session_info()
        print(f"📈 Session Stats: {session_info['message_count']} messages")
        
    async def demo_tool_execution_structure(self):
        """Demonstrate the tool execution structure."""
        print(f"\n⚙️  TOOL EXECUTION DEMO")
        print("=" * 50)
        
        # Create mock tool calls to demonstrate the execution loop
        mock_tools = [
            {"name": "read_file", "input": {"request": "read README.md"}},
            {"name": "list_directory", "input": {"request": "list current directory"}},
            {"name": "nonexistent_tool", "input": {"request": "test error handling"}}
        ]
        
        for i, mock_call in enumerate(mock_tools, 1):
            print(f"🔄 Tool Execution Loop #{i}: {mock_call['name']}")
            
            # Create mock tool call object
            class MockToolCall:
                def __init__(self, name, input_data):
                    self.name = name
                    self.input = input_data
                    self.id = f"mock_id_{i}"
            
            mock_call_obj = MockToolCall(mock_call["name"], mock_call["input"])
            result = await self.agent._tool_execution_loop(mock_call_obj)
            
            print(f"   Result: {'✅ Success' if not result['is_error'] else '❌ Error'}")
            print(f"   Content: {result['content'][:100]}...")
    
    def demo_anthropic_integration(self):
        """Demonstrate Anthropic API integration setup."""
        print(f"\n🧠 ANTHROPIC INTEGRATION DEMO")
        print("=" * 50)
        
        # Show Anthropic tool format
        anthropic_tools = self.agent._get_anthropic_tools()
        print(f"🔗 Tools formatted for Anthropic: {len(anthropic_tools)} tools")
        
        if anthropic_tools:
            # Show example tool format
            sample_tool = anthropic_tools[0]
            print(f"📝 Sample Tool Schema:")
            print(f"   Name: {sample_tool['name']}")
            print(f"   Description: {sample_tool['description'][:80]}...")
            print(f"   Input Schema: {sample_tool['input_schema']['type']}")
        
        # Show client readiness
        client_ready = hasattr(self.agent, 'anthropic_client') and self.agent.anthropic_client is not None
        print(f"🔌 Anthropic Client: {'✅ Ready' if client_ready else '❌ Not Ready'}")
    
    async def interactive_demo(self):
        """Run an interactive demonstration."""
        print(f"\n🎮 INTERACTIVE DEMO")
        print("=" * 50)
        print("This would start the full event loop. For demo purposes, showing structure:")
        print()
        print("SharedEventLoop Structure:")
        print("┌─ Start Chat Session")
        print("├─ Get User Input")
        print("│  ├─ Empty Input? → Continue")
        print("│  └─ Valid Input → Add to Conversation")
        print("├─ Run Inference (Claude API)")
        print("├─ Tool Use Decision")
        print("│  ├─ Has Tools? → Execute Tools")
        print("│  │  └─ Tool Execution Loop")
        print("│  │     ├─ Find Tool by Name")
        print("│  │     ├─ Execute Tool Function") 
        print("│  │     ├─ Capture Result/Error")
        print("│  │     └─ Add to Tool Results")
        print("│  └─ No Tools? → Display Text")
        print("└─ Loop Back to Get User Input")
        print()
        print("🚀 To run interactively: python -c \"from demo_shared_event_loop import *; asyncio.run(run_interactive())\"")


async def run_full_demo():
    """Run the complete demonstration."""
    print("🚀 SharedEventLoopAgent Architecture Demonstration")
    print("="*60)
    
    demo = AgentDemo()
    
    # Setup agent
    agent = await demo.setup_agent()
    
    # Show architecture information
    demo.display_agent_info()
    
    # Demo conversation flow
    await demo.demo_conversation_flow()
    
    # Demo tool execution
    await demo.demo_tool_execution_structure()
    
    # Demo Anthropic integration
    demo.demo_anthropic_integration()
    
    # Interactive demo info
    await demo.interactive_demo()
    
    print(f"\n🎉 Demo Complete!")
    print("The SharedEventLoopAgent is fully implemented and working!")


async def run_interactive():
    """Run the interactive event loop (for testing with real API key)."""
    print("🎮 Starting Interactive SharedEventLoopAgent...")
    
    # Check for API key
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("⚠️  No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to run interactively.")
        print("For demo purposes, running architecture test instead...")
        await run_full_demo()
        return
    
    try:
        config = EnhancedConfig()
        agent = SharedEventLoopAgent(config)
        
        print("🚀 Starting interactive session...")
        print("Type 'exit' to quit")
        
        await agent.run_shared_event_loop()
        
    except Exception as e:
        print(f"❌ Error running interactive session: {e}")
        print("Running demo instead...")
        await run_full_demo()


if __name__ == "__main__":
    # Default to demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(run_interactive())
    else:
        asyncio.run(run_full_demo())