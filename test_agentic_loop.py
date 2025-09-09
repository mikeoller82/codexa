#!/usr/bin/env python3
"""
Test script for the Codexa Agentic Loop System
"""

import asyncio
import sys
from pathlib import Path

# Add codexa to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.agentic_loop import CodexaAgenticLoop, create_agentic_loop


async def test_basic_agentic_loop():
    """Test basic agentic loop functionality."""
    print("🔬 Testing Basic Agentic Loop System")
    print("=" * 50)
    
    # Create agentic loop instance
    loop = create_agentic_loop(
        config=None,  # Use without config for basic testing
        max_iterations=5,
        verbose=True
    )
    
    # Test a simple task
    task = "Create a simple hello world script"
    
    print(f"Task: {task}")
    print("\nStarting agentic loop...")
    print("-" * 30)
    
    try:
        result = await loop.run_agentic_loop(task)
        
        print("\n" + "=" * 50)
        print("🎉 Test Results Summary")
        print("=" * 50)
        print(f"Status: {result.status.value}")
        print(f"Success: {result.success}")
        print(f"Iterations: {len(result.iterations)}")
        print(f"Total Duration: {result.total_duration:.2f}s")
        
        if result.final_result:
            print(f"Final Result: {result.final_result}")
        
        # Show iteration summary
        print("\n📋 Iteration Summary:")
        for i, iteration in enumerate(result.iterations, 1):
            print(f"  {i}. {'✅' if iteration.success else '❌'} - {iteration.duration:.2f}s")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


async def test_command_integration():
    """Test command system integration."""
    print("\n🔗 Testing Command Integration")
    print("=" * 50)
    
    try:
        # Test importing the agentic commands
        from codexa.commands.agentic_commands import AGENTIC_COMMANDS
        
        print(f"✅ Successfully imported {len(AGENTIC_COMMANDS)} agentic commands:")
        for cmd_class in AGENTIC_COMMANDS:
            cmd = cmd_class()
            print(f"  • /{cmd.name} - {cmd.description}")
            print(f"    Aliases: {cmd.aliases}")
            print(f"    Parameters: {len(cmd.parameters)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Command integration test failed: {e}")
        return False


async def test_agentic_loop_components():
    """Test individual components of the agentic loop."""
    print("\n🧩 Testing Agentic Loop Components")
    print("=" * 50)
    
    try:
        loop = CodexaAgenticLoop(max_iterations=3, verbose=False)
        
        # Test thinking step
        print("Testing thinking step...")
        thinking_result = await loop._think_step("test task", 1)
        assert "thinking" in thinking_result
        assert "plan" in thinking_result
        print("✅ Thinking step works")
        
        # Test execution step
        print("Testing execution step...")
        execution_result = await loop._execute_step("test plan", 1)
        assert "result" in execution_result
        print("✅ Execution step works")
        
        # Test evaluation step
        print("Testing evaluation step...")
        evaluation_result = await loop._evaluate_step(execution_result, "test context", "test plan")
        assert "success" in evaluation_result
        assert "feedback" in evaluation_result
        print("✅ Evaluation step works")
        
        # Test refinement step
        print("Testing refinement step...")
        refined = await loop._refine_task("test task", "test feedback")
        assert isinstance(refined, str)
        assert len(refined) > 0
        print("✅ Refinement step works")
        
        return True
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False


def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing Module Imports")
    print("=" * 50)
    
    success = True
    
    # Test core agentic loop import
    try:
        from codexa.agentic_loop import CodexaAgenticLoop, create_agentic_loop
        print("✅ Core agentic loop modules imported successfully")
    except Exception as e:
        print(f"❌ Failed to import core agentic loop: {e}")
        success = False
    
    # Test command imports
    try:
        from codexa.commands.agentic_commands import AGENTIC_COMMANDS
        print("✅ Agentic commands imported successfully")
    except Exception as e:
        print(f"❌ Failed to import agentic commands: {e}")
        success = False
    
    # Test integration with built-in commands
    try:
        from codexa.commands.built_in_commands import BuiltInCommands
        print("✅ Built-in commands integration available")
    except Exception as e:
        print(f"❌ Failed to import built-in commands: {e}")
        success = False
    
    return success


async def main():
    """Run all tests."""
    print("🤖 Codexa Agentic Loop System Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        ("Import Test", test_imports),
        ("Component Test", test_agentic_loop_components),
        ("Command Integration Test", test_command_integration),
        ("Basic Agentic Loop Test", test_basic_agentic_loop),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The agentic loop system is ready to use.")
        print("\n💡 Try it out with:")
        print("   codexa")
        print("   /agentic \"create a hello world python script\"")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)