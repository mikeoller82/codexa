#!/usr/bin/env python3
"""
Test script for model discovery functionality.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the codexa package to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.config import Config
from codexa.services.model_service import ModelService, InteractiveModelSelector
from codexa.providers import ProviderFactory


async def test_model_discovery():
    """Test the model discovery functionality."""
    print("🧪 Testing Model Discovery System")
    print("=" * 50)
    
    # Initialize config
    config = Config()
    
    # Check for API keys
    available_providers = config.get_available_providers()
    print(f"Available providers: {available_providers}")
    
    if not available_providers:
        print("❌ No API keys configured. Please set:")
        print("  - OPENAI_API_KEY")
        print("  - ANTHROPIC_API_KEY") 
        print("  - OPENROUTER_API_KEY")
        return False
    
    # Test provider model fetching
    print("\n📡 Testing provider model fetching...")
    
    for provider in available_providers:
        print(f"\n🔍 Testing {provider}...")
        try:
            # Create provider instance
            factory = ProviderFactory()
            temp_config = Config()
            temp_config.default_provider = provider
            
            provider_instance = factory.create_provider(temp_config)
            if provider_instance and hasattr(provider_instance, 'get_available_models'):
                models = provider_instance.get_available_models()
                print(f"✅ {provider}: Found {len(models)} models")
                
                # Show first 3 models
                for i, model in enumerate(models[:3]):
                    model_name = model.get('name', model.get('id', 'Unknown'))
                    print(f"  - {model_name}")
                
                if len(models) > 3:
                    print(f"  ... and {len(models) - 3} more")
            else:
                print(f"⚠️  {provider}: Provider doesn't support model discovery")
                
        except Exception as e:
            print(f"❌ {provider}: Error - {e}")
    
    # Test model service
    print("\n🔧 Testing ModelService...")
    
    model_service = ModelService(config)
    
    try:
        print("Discovering models from all providers (30s timeout)...")
        discovery_results = model_service.discover_all_models(timeout=30.0)
        
        print(f"\n📊 Discovery Results:")
        total_models = 0
        
        for provider, result in discovery_results.items():
            if result.success:
                total_models += len(result.models)
                print(f"✅ {provider}: {len(result.models)} models ({result.response_time:.2f}s)")
            else:
                print(f"❌ {provider}: Failed - {result.error}")
        
        print(f"\n🎯 Total models discovered: {total_models}")
        
        # Test model info conversion
        if total_models > 0:
            print("\n🔄 Converting to ModelInfo objects...")
            model_infos = model_service.convert_to_model_info(discovery_results)
            print(f"✅ Converted {len(model_infos)} models")
            
            # Show some examples
            print("\nExample models:")
            for i, model in enumerate(model_infos[:5]):
                print(f"  {i+1}. {model.display_name} ({model.provider}) - {model.cost_tier}")
        
        # Test caching
        print("\n💾 Testing cache functionality...")
        stats = model_service.get_provider_statistics()
        for provider, stat in stats.items():
            if stat['success']:
                print(f"✅ {provider} cache: {stat['model_count']} models")
        
        return True
        
    except Exception as e:
        print(f"❌ ModelService test failed: {e}")
        return False


async def test_interactive_selection():
    """Test interactive model selection (if TTY available)."""
    if not sys.stdin.isatty():
        print("⏭️  Skipping interactive test (not running in TTY)")
        return True
    
    print("\n🎮 Testing Interactive Model Selection")
    print("=" * 50)
    
    config = Config()
    available_providers = config.get_available_providers()
    
    if not available_providers:
        print("⏭️  No providers available for interactive test")
        return True
    
    try:
        model_service = ModelService(config)
        selector = InteractiveModelSelector(model_service)
        
        print("Starting interactive model selection...")
        print("(Press Ctrl+C to skip)")
        
        try:
            result = await selector.select_model_interactive()
            
            if result:
                provider, model_name = result
                print(f"✅ Selected: {model_name} ({provider})")
                return True
            else:
                print("ℹ️  No model selected")
                return True
                
        except (KeyboardInterrupt, EOFError):
            print("\n⏭️  Interactive test skipped by user")
            return True
            
    except Exception as e:
        print(f"❌ Interactive test failed: {e}")
        return False


def test_basic_config():
    """Test basic configuration functionality."""
    print("⚙️  Testing Configuration System")
    print("=" * 50)
    
    try:
        config = Config()
        
        # Test provider switching
        providers = config.get_available_providers()
        if providers:
            original_provider = config.get_provider()
            
            for provider in providers:
                success = config.switch_provider(provider)
                if success:
                    current = config.get_provider()
                    print(f"✅ Provider switch: {original_provider} → {current}")
                    
                    # Test model switching
                    test_model = "test-model-123"
                    success = config.switch_model(test_model, provider)
                    if success:
                        current_model = config.get_model(provider)
                        print(f"✅ Model switch: {current_model}")
                    break
        
        # Test model listing
        for provider in providers[:2]:  # Test first 2 providers
            models = config.get_available_models(provider)
            print(f"✅ {provider} models: {models}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Codexa Model Discovery Test Suite")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_basic_config),
        ("Model Discovery", test_model_discovery),
        ("Interactive Selection", test_interactive_selection),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n📋 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The model discovery system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == len(results)


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        sys.exit(1)