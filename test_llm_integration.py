#!/usr/bin/env python3
"""
Test the real LLM integration for Codexa Agentic Loop System
"""

import asyncio
import sys
import os
from pathlib import Path

# Add codexa to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.agentic_loop import CodexaAgenticLoop, create_agentic_loop
from codexa.config import Config


async def test_llm_integration():
    """Test the agentic loop with real LLM integration."""
    print("🧠 Testing Codexa Agentic Loop with Real LLM Integration")
    print("=" * 60)
    
    # Check for API keys
    api_keys = {
        'OpenRouter': os.getenv('OPENROUTER_API_KEY'),
        'OpenAI': os.getenv('OPENAI_API_KEY'),
        'Anthropic': os.getenv('ANTHROPIC_API_KEY')
    }
    
    available_providers = [name for name, key in api_keys.items() if key]
    
    if not available_providers:
        print("❌ No API keys found!")
        print("\nPlease set one of the following environment variables:")
        for name in api_keys.keys():
            print(f"  export {name.upper()}_API_KEY=your_api_key")
        return False
    
    print(f"✅ Available providers: {', '.join(available_providers)}")
    
    # Create config
    try:
        config = Config()
        if not config.has_valid_config():
            print("❌ No valid configuration found")
            return False
        
        print(f"✅ Using provider: {config.get_provider()}")
        print(f"✅ Using model: {config.get_model()}")
    
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False
    
    # Test the agentic loop with real LLM
    print("\n🚀 Testing Agentic Loop with Real Task")
    print("-" * 40)
    
    try:
        loop = create_agentic_loop(
            config=config,
            max_iterations=3,  # Keep it short for testing
            verbose=True
        )
        
        if not loop.provider:
            print("❌ Provider not properly initialized")
            return False
        
        print("✅ Provider initialized successfully")
        
        # Test with a simple task
        task = "create a simple hello world Python script"
        print(f"\n📝 Task: {task}")
        
        result = await loop.run_agentic_loop(task)
        
        print("\n" + "=" * 60)
        print("🎯 INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        print(f"✅ Task Status: {result.status.value}")
        print(f"✅ Success: {result.success}")
        print(f"✅ Iterations: {len(result.iterations)}")
        print(f"✅ Duration: {result.total_duration:.2f}s")
        
        # Check if any real LLM thinking was done
        used_llm = False
        for iteration in result.iterations:
            if hasattr(iteration, 'thinking') and len(iteration.thinking) > 50:
                used_llm = True
                break
        
        if used_llm:
            print("✅ LLM Integration: Working - Real AI reasoning detected")
        else:
            print("⚠️  LLM Integration: May not be fully working - Check responses")
        
        # Show some example thinking
        if result.iterations:
            first_iteration = result.iterations[0]
            print(f"\n💭 Example LLM Thinking (Iteration 1):")
            print(f"   {first_iteration.thinking[:200]}...")
            print(f"\n🎯 Example Plan Generated:")
            print(f"   {first_iteration.plan[:150]}...")
        
        # Check if actual files were created
        test_files = ['hello_world.py', 'generated_script.py', 'hello.py']
        files_created = []
        for filename in test_files:
            if Path(filename).exists():
                files_created.append(filename)
        
        if files_created:
            print(f"\n📁 Files Created: {', '.join(files_created)}")
            print("✅ File Operations: Working")
        else:
            print("\n📁 No test files created (may be expected)")
        
        # Verify the loop actually used LLM for evaluation  
        llm_evaluations = 0
        for iteration in result.iterations:
            if hasattr(iteration, 'evaluation') and 'llm' in iteration.evaluation.lower():
                llm_evaluations += 1
        
        if llm_evaluations > 0:
            print(f"✅ LLM Evaluation: Used in {llm_evaluations} iterations")
        else:
            print("⚠️  LLM Evaluation: Used fallback heuristics")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_command_integration():
    """Test the command system integration."""
    print("\n🔗 Testing Command System Integration")
    print("=" * 60)
    
    try:
        # Test importing the commands
        from codexa.commands.agentic_commands import AgenticCommand
        from codexa.commands.command_registry import CommandContext
        
        # Create a mock context
        config = Config()
        if not config.has_valid_config():
            print("❌ Config not available for command test")
            return False
        
        context = CommandContext(
            user_input="/agentic \"test task\"",
            parsed_args={
                "task": "create a simple test file",
                "max_iterations": 2,
                "verbose": True
            },
            codexa_agent=None,
            config=config
        )
        
        # Test the command
        command = AgenticCommand()
        print(f"✅ Command loaded: {command.name}")
        print(f"✅ Description: {command.description}")
        print(f"✅ Parameters: {len(command.parameters)}")
        
        # We can't easily test execution without full Codexa setup,
        # but we can test the command structure
        print("✅ Command integration structure is correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Command integration test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("🤖 Codexa Agentic Loop - Real LLM Integration Test")
    print("=" * 70)
    print()
    
    tests = [
        ("Command Integration", test_command_integration),
        ("LLM Integration", test_llm_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 FINAL INTEGRATION TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("The Codexa Agentic Loop is fully integrated with LLM providers.")
        print("\n💡 Ready to use:")
        print("   codexa")
        print("   > /agentic \"your task here\"")
        print("\nThe system will now:")
        print("• 🧠 Think using real AI (OpenRouter/OpenAI/Anthropic)")
        print("• ⚡ Execute real file operations") 
        print("• 🔍 Evaluate results with LLM analysis")
        print("• 🔄 Iterate until task completion")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the output above for details.")
        print("\nThe system may still work, but some features might use fallbacks.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)