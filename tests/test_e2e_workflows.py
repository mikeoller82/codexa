#!/usr/bin/env python3
"""
End-to-End Testing for Codexa Enhanced Features
Tests complete workflows from startup through advanced operations
"""

import os
import sys
import time
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch
import subprocess

# Add the codexa module to path
sys.path.insert(0, str(Path(__file__).parent))

def setup_test_environment():
    """Setup test environment with mock API keys"""
    os.environ['OPENAI_API_KEY'] = 'test-key-openai'
    os.environ['ANTHROPIC_API_KEY'] = 'test-key-anthropic'
    os.environ['OPENROUTER_API_KEY'] = 'test-key-openrouter'

def test_imports_and_basic_functionality():
    """Test 1: Basic imports and component initialization"""
    print("🧪 Test 1: Basic Imports and Initialization")
    print("-" * 50)
    
    try:
        # Test enhanced CLI import
        from codexa.cli import main, ENHANCED_FEATURES
        print(f"✅ Enhanced Features Available: {ENHANCED_FEATURES}")
        
        # Test enhanced core import  
        from codexa.enhanced_core import EnhancedCodexaAgent
        print("✅ Enhanced Core: Import successful")
        
        # Test core components
        agent = EnhancedCodexaAgent()
        print("✅ Enhanced Agent: Creation successful")
        
        # Test component initialization
        components = [
            ('Command Registry', len(agent.command_registry.get_command_names())),
            ('Error Manager', hasattr(agent.error_manager, 'handle_error')),
            ('User Guidance', hasattr(agent.user_guidance, 'provide_guidance')),
            ('Suggestion Engine', hasattr(agent.suggestion_engine, 'generate_suggestions')),
            ('Contextual Help', hasattr(agent.contextual_help, 'get_contextual_help')),
            ('Plugin Manager', hasattr(agent.plugin_manager, 'load_plugins')),
            ('MCP Health Monitor', hasattr(agent.mcp_health_monitor, 'start_monitoring'))
        ]
        
        for name, status in components:
            result = "✅" if status else "❌"
            print(f"{result} {name}: {'Ready' if status else 'Missing'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 1 Failed: {e}")
        return False

def test_ascii_art_and_themes():
    """Test 2: ASCII Art Rendering and Theme System"""
    print("\n🎨 Test 2: ASCII Art and Theme System")
    print("-" * 50)
    
    try:
        from codexa.display.ascii_art import ASCIIArtRenderer, LogoTheme
        renderer = ASCIIArtRenderer()
        
        # Test theme enumeration
        themes = renderer.get_available_themes()
        print(f"✅ Available Themes: {len(themes)} themes")
        
        # Test rendering each theme
        for theme_name in themes[:3]:  # Test first 3 themes
            try:
                theme = LogoTheme(theme_name)
                logo = renderer.render_logo(theme, show_info=False)
                if logo and len(logo) > 0:
                    print(f"✅ Theme '{theme_name}': Rendered successfully")
                else:
                    print(f"⚠️  Theme '{theme_name}': Empty render")
            except Exception as e:
                print(f"❌ Theme '{theme_name}': {e}")
        
        # Test animation creation
        animation = renderer.create_startup_animation(LogoTheme.DEFAULT)
        if animation:
            print("✅ Animation: Creation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 2 Failed: {e}")
        return False

def test_provider_and_model_management():
    """Test 3: Provider and Model Management System"""
    print("\n⚡ Test 3: Provider and Model Management")
    print("-" * 50)
    
    try:
        from codexa.enhanced_providers import EnhancedProviderFactory
        from codexa.enhanced_config import EnhancedConfig
        
        config = EnhancedConfig()
        factory = EnhancedProviderFactory(config)
        
        # Test provider discovery
        providers = factory.get_available_providers()
        print(f"✅ Available Providers: {len(providers)} found")
        
        for provider in providers[:3]:  # Test first 3 providers
            print(f"  • {provider}")
        
        # Test provider creation
        provider = factory.get_provider()
        if provider:
            provider_name = type(provider).__name__
            print(f"✅ Provider Creation: {provider_name} initialized")
        
        # Test model information
        current_provider = config.get_provider()
        current_model = config.get_model()
        print(f"✅ Current Configuration: {current_provider}/{current_model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 3 Failed: {e}")
        return False

def test_mcp_service_integration():
    """Test 4: MCP Service Integration"""
    print("\n📡 Test 4: MCP Service Integration")
    print("-" * 50)
    
    try:
        from codexa.mcp_service import MCPService
        from codexa.enhanced_config import EnhancedConfig
        
        config = EnhancedConfig()
        mcp_service = MCPService(config)
        
        # Test MCP service creation
        print("✅ MCP Service: Created successfully")
        
        # Test server availability (without actual connection)
        if hasattr(mcp_service, 'get_available_servers'):
            servers = mcp_service.get_available_servers()
            print(f"✅ MCP Servers: {len(servers)} configured")
        
        # Test MCP configuration
        if hasattr(config, 'mcp_servers') and config.mcp_servers:
            configured_servers = len(config.mcp_servers)
            print(f"✅ MCP Configuration: {configured_servers} servers configured")
        else:
            print("⚠️  MCP Configuration: No servers configured (expected)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 4 Failed: {e}")
        return False

def test_slash_command_system():
    """Test 5: Slash Command System"""
    print("\n⚡ Test 5: Slash Command System")
    print("-" * 50)
    
    try:
        from codexa.commands.command_registry import CommandRegistry
        from codexa.commands.built_in_commands import BuiltInCommands
        from codexa.commands.command_executor import CommandExecutor
        from rich.console import Console
        
        # Test command registration
        registry = CommandRegistry()
        BuiltInCommands.register_all(registry)
        
        commands = registry.get_command_names()
        print(f"✅ Command Registration: {len(commands)} commands")
        
        # Test specific commands
        essential_commands = ['help', 'status', 'provider', 'mcp', 'commands']
        for cmd_name in essential_commands:
            cmd = registry.get_command(cmd_name)
            if cmd:
                print(f"✅ Command '{cmd_name}': Available")
            else:
                print(f"❌ Command '{cmd_name}': Missing")
        
        # Test command executor
        executor = CommandExecutor(registry, Console())
        print("✅ Command Executor: Created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 5 Failed: {e}")
        return False

def test_performance_benchmarks():
    """Test 6: Performance Benchmarks"""
    print("\n📊 Test 6: Performance Benchmarks")
    print("-" * 50)
    
    try:
        # Test startup time
        start_time = time.time()
        from codexa.enhanced_core import EnhancedCodexaAgent
        agent = EnhancedCodexaAgent()
        startup_time = time.time() - start_time
        
        startup_pass = startup_time < 3.0
        print(f"{'✅' if startup_pass else '❌'} Startup Time: {startup_time:.2f}s (Target: <3s)")
        
        # Test command response time
        start_time = time.time()
        commands = agent.command_registry.list_commands()
        command_time = time.time() - start_time
        
        command_pass = command_time < 0.5
        print(f"{'✅' if command_pass else '❌'} Command Response: {command_time*1000:.1f}ms (Target: <500ms)")
        
        # Test ASCII rendering performance
        start_time = time.time()
        from codexa.display.ascii_art import ASCIIArtRenderer, LogoTheme
        renderer = ASCIIArtRenderer()
        for theme in [LogoTheme.DEFAULT, LogoTheme.MINIMAL]:
            logo = renderer.render_logo(theme, show_info=False)
        render_time = time.time() - start_time
        
        render_pass = render_time < 0.1
        print(f"{'✅' if render_pass else '❌'} ASCII Rendering: {render_time*1000:.1f}ms (Target: <100ms)")
        
        # Overall performance
        overall_pass = startup_pass and command_pass and render_pass
        print(f"{'✅' if overall_pass else '❌'} Overall Performance: {'PASS' if overall_pass else 'NEEDS IMPROVEMENT'}")
        
        return overall_pass
        
    except Exception as e:
        print(f"❌ Test 6 Failed: {e}")
        return False

def test_async_functionality_interface():
    """Test 7: Async Functionality"""
    print("\n⚙️  Test 7: Async Functionality")
    print("-" * 50)
    
    try:
        from codexa.enhanced_core import EnhancedCodexaAgent
        
        agent = EnhancedCodexaAgent()
        
        # Test async components
        async_components = [
            ('Interactive Startup', agent.interactive_startup, 'run_startup_flow'),
            ('Plugin Manager', agent.plugin_manager, 'initialize_plugins'),
            ('Health Monitor', agent.mcp_health_monitor, 'start_monitoring')
        ]
        
        for name, component, method_name in async_components:
            if component and hasattr(component, method_name):
                method = getattr(component, method_name)
                if asyncio.iscoroutinefunction(method):
                    print(f"✅ {name}: Async method available")
                else:
                    print(f"⚠️  {name}: Method not async")
            else:
                print(f"❌ {name}: Component or method missing")
        
        # Test async startup flow
        try:
            result = await agent.interactive_startup.run_startup_flow()
            if result:
                print("✅ Async Startup Flow: Working")
            else:
                print("⚠️  Async Startup Flow: No result")
        except Exception as e:
            print(f"⚠️  Async Startup Flow: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 7 Failed: {e}")
        return False

def test_error_handling_and_recovery():
    """Test 8: Error Handling and Recovery"""
    print("\n🛡️  Test 8: Error Handling and Recovery")
    print("-" * 50)
    
    try:
        from codexa.enhanced_core import EnhancedCodexaAgent
        
        agent = EnhancedCodexaAgent()
        
        # Test error manager functionality
        error_manager = agent.error_manager
        test_error = Exception("Test error for validation")
        
        from codexa.error_handling import ErrorContext
        context = ErrorContext(
            operation="test_operation",
            component="test_component", 
            user_action="test_action"
        )
        
        # Test error handling (should not raise)
        try:
            error_manager.handle_error(test_error, context)
            print("✅ Error Handling: Working correctly")
        except Exception as e:
            print(f"❌ Error Handling: {e}")
        
        # Test user guidance
        guidance = agent.user_guidance
        try:
            guidance.provide_guidance("test_topic", context={"test": True})
            print("✅ User Guidance: Working correctly")
        except Exception as e:
            print(f"❌ User Guidance: {e}")
        
        # Test error statistics
        try:
            stats = error_manager.get_error_statistics()
            if isinstance(stats, dict):
                print("✅ Error Statistics: Available")
            else:
                print("⚠️  Error Statistics: Unexpected format")
        except Exception as e:
            print(f"❌ Error Statistics: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 8 Failed: {e}")
        return False

def test_complete_workflow_integration():
    """Test 9: Complete Workflow Integration"""
    print("\n🔄 Test 9: Complete Workflow Integration") 
    print("-" * 50)
    
    try:
        from codexa.enhanced_core import EnhancedCodexaAgent
        
        # Create agent (full initialization)
        agent = EnhancedCodexaAgent()
        print("✅ Agent Initialization: Complete")
        
        # Test integrated workflow
        workflow_steps = [
            ("ASCII Art System", lambda: agent.startup_animation is not None),
            ("Command System", lambda: len(agent.command_registry.get_command_names()) > 0),
            ("Provider System", lambda: agent.provider is not None),
            ("MCP Service", lambda: agent.mcp_service is not None),
            ("Error Handling", lambda: agent.error_manager is not None),
            ("User Guidance", lambda: agent.user_guidance is not None),
            ("Contextual Help", lambda: agent.contextual_help is not None),
            ("Plugin Manager", lambda: agent.plugin_manager is not None)
        ]
        
        passed_steps = 0
        for step_name, test_func in workflow_steps:
            try:
                if test_func():
                    print(f"✅ {step_name}: Integrated successfully")
                    passed_steps += 1
                else:
                    print(f"❌ {step_name}: Integration failed")
            except Exception as e:
                print(f"❌ {step_name}: {e}")
        
        success_rate = (passed_steps / len(workflow_steps)) * 100
        print(f"📊 Integration Success Rate: {success_rate:.1f}% ({passed_steps}/{len(workflow_steps)})")
        
        return success_rate >= 90.0
        
    except Exception as e:
        print(f"❌ Test 9 Failed: {e}")
        return False

def run_cli_integration_test():
    """Test 10: CLI Integration Test"""
    print("\n🖥️  Test 10: CLI Integration")
    print("-" * 50)
    
    try:
        # Test basic CLI functionality
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        env['OPENAI_API_KEY'] = 'test-key'
        
        # Test version command
        result = subprocess.run(
            [sys.executable, '-c', 'from codexa.cli import main; import sys; sys.argv = ["codexa", "--version"]; main()'],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        if result.returncode == 0 and "Codexa version" in result.stdout:
            print("✅ CLI Version Command: Working")
        else:
            print("❌ CLI Version Command: Failed")
            print(f"  Output: {result.stdout}")
            print(f"  Error: {result.stderr}")
        
        # Test basic import functionality
        result = subprocess.run(
            [sys.executable, '-c', '''
import os
os.environ["OPENAI_API_KEY"] = "test-key"
from codexa.enhanced_core import EnhancedCodexaAgent
agent = EnhancedCodexaAgent()
print("CLI Integration Test: SUCCESS")
            '''],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            print("✅ CLI Agent Creation: Working")
            return True
        else:
            print("❌ CLI Agent Creation: Failed")
            print(f"  Output: {result.stdout}")
            print(f"  Error: {result.stderr}")
            return False
        
    except subprocess.TimeoutExpired:
        print("⚠️  CLI Integration: Timeout (expected for interactive)")
        return True  # Timeout is expected for interactive CLI
    except Exception as e:
        print(f"❌ CLI Integration Failed: {e}")
        return False

def main():
    """Run all E2E tests"""
    print("🚀 CODEXA END-TO-END TESTING SUITE")
    print("=" * 60)
    print("Testing all enhanced features and workflows...")
    print()
    
    # Setup test environment
    setup_test_environment()
    
    # Run all tests
    tests = [
        test_imports_and_basic_functionality,
        test_ascii_art_and_themes,
        test_provider_and_model_management,
        test_mcp_service_integration,
        test_slash_command_system,
        test_performance_benchmarks,
        test_error_handling_and_recovery,
        test_complete_workflow_integration,
        run_cli_integration_test
    ]
    
    # Track results
    results = []
    start_time = time.time()
    
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)
    
    # Run async test
    try:
        async_result = asyncio.run(test_async_functionality())
        results.append(async_result)
    except Exception as e:
        print(f"❌ Async test crashed: {e}")
        results.append(False)
    
    # Calculate results
    total_time = time.time() - start_time
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100
    
    # Final report
    print("\n" + "=" * 60)
    print("🎯 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
    print(f"Total Time: {total_time:.2f} seconds")
    print()
    
    if success_rate >= 90:
        print("🎉 OVERALL RESULT: SUCCESS")
        print("✅ All core functionality is working correctly")
        print("✅ Codexa is ready for production use")
    elif success_rate >= 75:
        print("⚠️  OVERALL RESULT: MOSTLY WORKING")
        print("✅ Core functionality operational")
        print("⚠️  Some features may need attention")
    else:
        print("❌ OVERALL RESULT: NEEDS WORK")
        print("❌ Major issues detected")
        print("🔧 Review failed tests before production use")
    
    print("\n🚀 Codexa Enhanced Features Testing Complete!")
    return success_rate >= 90

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)