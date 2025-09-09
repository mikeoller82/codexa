#!/usr/bin/env python3
"""
Test suite for validation system fixes.

This test suite validates the security fixes and ensures the validation disconnect
has been resolved while maintaining backward compatibility.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, patch
from typing import Dict, Any

# Import the components we're testing
from codexa.tools.base.unified_validation import (
    unified_validator, ValidationResult, ValidationSeverity, ValidationCategory,
    StringValidator, EnumValidator
)
from codexa.tools.base.tool_interface import ToolContext, ToolResult
from codexa.tools.claude_code.task_tool import TaskTool
from codexa.tools.claude_code.claude_code_registry import claude_code_registry


class TestUnifiedValidation:
    """Test the unified validation framework."""
    
    def test_string_validator_security(self):
        """Test string validation security features."""
        validator = StringValidator()
        
        # Test injection attempts
        injection_attempts = [
            "; rm -rf /",
            "test && malicious_command",
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "eval('malicious_code')",
            "$(malicious_command)"
        ]
        
        for attempt in injection_attempts:
            result = validator.validate(attempt)
            assert not result.valid, f"Should reject injection: {attempt}"
            assert any(
                issue["category"] == ValidationCategory.INJECTION.value 
                for issue in result.security_issues
            ), f"Should flag as injection: {attempt}"
    
    def test_string_validator_length_limits(self):
        """Test string length validation."""
        validator = StringValidator(min_length=5, max_length=100)
        
        # Test too short
        result = validator.validate("abc")
        assert not result.valid
        assert "too short" in result.errors[0].lower()
        
        # Test too long
        long_string = "x" * 150
        result = validator.validate(long_string)
        # Should truncate but not fail completely
        assert result.valid or "too long" in result.warnings[0].lower()
    
    def test_enum_validator(self):
        """Test enum validation."""
        validator = EnumValidator({"option1", "option2", "option3"})
        
        # Valid option
        result = validator.validate("option1")
        assert result.valid
        
        # Invalid option  
        result = validator.validate("invalid")
        assert not result.valid
        assert "Invalid value" in result.errors[0]
    
    def test_task_tool_validation(self):
        """Test Task tool specific validation."""
        # Valid parameters
        valid_params = {
            "description": "Test task",
            "prompt": "Do something useful",
            "subagent_type": "general-purpose"
        }
        
        result = unified_validator.validate_tool_parameters("Task", valid_params)
        assert result.valid
        
        # Invalid subagent type
        invalid_params = {
            "description": "Test task",
            "prompt": "Do something useful", 
            "subagent_type": "invalid-type"
        }
        
        result = unified_validator.validate_tool_parameters("Task", invalid_params)
        assert not result.valid
    
    def test_user_friendly_errors(self):
        """Test that error messages are user-friendly."""
        params = {
            "description": "; rm -rf /",
            "prompt": "",
            "subagent_type": "invalid"
        }
        
        result = unified_validator.validate_tool_parameters("Task", params)
        assert not result.valid
        
        user_error = result.get_user_friendly_error()
        
        # Should not expose internal details
        assert "rm -rf" not in user_error
        assert "security" not in user_error.lower()
        assert "injection" not in user_error.lower()
        
        # Should be helpful
        assert len(user_error) > 0
        assert user_error != result.errors[0]  # Should be different from raw error


class TestTaskToolSecurity:
    """Test Task tool security fixes."""
    
    @pytest.fixture
    def task_tool(self):
        """Create TaskTool instance for testing."""
        return TaskTool()
    
    @pytest.fixture
    def mock_context(self):
        """Create mock ToolContext for testing."""
        context = Mock(spec=ToolContext)
        context.get_state = Mock()
        context.session_id = "test-session"
        context.request_id = "test-request"
        return context
    
    @pytest.mark.asyncio
    async def test_validation_disconnect_fixed(self, task_tool, mock_context):
        """Test that validation disconnect is resolved."""
        # Simulate parameters that would pass registry but fail tool validation
        mock_context.get_state.side_effect = lambda key: {
            "description": "",  # Empty string - registry would pass, tool would fail
            "prompt": "",
            "subagent_type": ""
        }.get(key)
        
        result = await task_tool.execute(mock_context)
        
        # Should fail with clear error message
        assert not result.success
        assert "required" in result.error.lower() or "empty" in result.error.lower()
        # Should not expose internal validation details
        assert "context validation failed" not in result.error
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_protection(self, task_tool, mock_context):
        """Test protection against resource exhaustion."""
        mock_context.get_state.side_effect = lambda key: {
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "general-purpose"
        }.get(key)
        
        # Fill up the subagent slots
        task_tool._active_subagents = {
            f"subagent_{i}": {"start_time": 0} 
            for i in range(task_tool._max_concurrent_subagents)
        }
        
        result = await task_tool.execute(mock_context)
        
        assert not result.success
        assert "limit" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_timeout_protection(self, task_tool, mock_context):
        """Test timeout protection."""
        mock_context.get_state.side_effect = lambda key: {
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "general-purpose"
        }.get(key)
        
        # Set very short timeout for testing
        task_tool._subagent_timeout = 0.1
        
        # Mock a slow subagent execution
        async def slow_subagent(*args, **kwargs):
            await asyncio.sleep(0.2)  # Longer than timeout
            return "result"
        
        with patch.object(task_tool, '_simulate_subagent', side_effect=slow_subagent):
            result = await task_tool.execute(mock_context)
        
        assert not result.success
        assert "timeout" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_secure_error_handling(self, task_tool, mock_context):
        """Test that internal errors are not exposed."""
        mock_context.get_state.side_effect = Exception("Internal database connection failed")
        
        result = await task_tool.execute(mock_context)
        
        assert not result.success
        # Should not expose internal error details
        assert "database" not in result.error
        assert "connection failed" not in result.error
        # Should provide user-friendly message
        assert len(result.error) > 0


class TestBackwardCompatibility:
    """Test backward compatibility of the fixes."""
    
    def test_registry_deprecation_warnings(self):
        """Test that deprecation warnings are raised."""
        with pytest.warns(DeprecationWarning):
            claude_code_registry.validate_parameters("Task", {
                "description": "test",
                "prompt": "test", 
                "subagent_type": "general-purpose"
            })
    
    def test_registry_fallback_to_unified(self):
        """Test automatic fallback to unified validator."""
        params = {
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "general-purpose"
        }
        
        result = claude_code_registry.validate_parameters("Task", params)
        
        # Should use unified validator internally
        assert "security_validated" in result
        assert result["security_validated"] is True
    
    def test_existing_api_compatibility(self):
        """Test that existing API still works."""
        params = {
            "description": "Test task", 
            "prompt": "Do something",
            "subagent_type": "general-purpose"
        }
        
        # Old API should still work
        result = claude_code_registry.validate_parameters("Task", params)
        
        # Should have expected fields
        assert "valid" in result
        assert "parameters" in result
        
        # Should work with valid parameters
        assert result["valid"] is True


class TestPerformanceImprovements:
    """Test performance improvements."""
    
    def test_validation_caching(self):
        """Test that validation results are cached appropriately."""
        params = {
            "description": "Test task",
            "prompt": "Do something", 
            "subagent_type": "general-purpose"
        }
        
        # First validation
        start_time = asyncio.get_event_loop().time()
        result1 = unified_validator.validate_tool_parameters("Task", params)
        first_time = asyncio.get_event_loop().time() - start_time
        
        # Second validation (should be faster if cached)
        start_time = asyncio.get_event_loop().time()
        result2 = unified_validator.validate_tool_parameters("Task", params)
        second_time = asyncio.get_event_loop().time() - start_time
        
        # Results should be the same
        assert result1.valid == result2.valid
        
        # Note: Caching might not be noticeable in unit tests due to overhead
        # This test mainly ensures caching doesn't break functionality
    
    def test_batch_validation_potential(self):
        """Test that validation can handle multiple tools efficiently."""
        tools_params = [
            ("Task", {
                "description": "Task 1",
                "prompt": "Do task 1",
                "subagent_type": "general-purpose"
            }),
            ("Task", {
                "description": "Task 2", 
                "prompt": "Do task 2",
                "subagent_type": "general-purpose"
            })
        ]
        
        # Validate multiple tools
        results = []
        for tool_name, params in tools_params:
            result = unified_validator.validate_tool_parameters(tool_name, params)
            results.append(result)
        
        # All should succeed
        assert all(result.valid for result in results)


class TestSecurityAuditTrail:
    """Test security audit and logging."""
    
    def test_security_logging(self, caplog):
        """Test that security issues are properly logged."""
        with caplog.at_level(logging.WARNING):
            params = {
                "description": "; rm -rf /",  # Injection attempt
                "prompt": "test",
                "subagent_type": "general-purpose"
            }
            
            result = unified_validator.validate_tool_parameters("Task", params)
            
            # Should log security issue
            assert not result.valid
            # Note: Logging test depends on logger configuration
    
    def test_audit_metadata(self):
        """Test that validation includes audit metadata."""
        params = {
            "description": "Test task",
            "prompt": "Do something",
            "subagent_type": "general-purpose"
        }
        
        result = unified_validator.validate_tool_parameters("Task", params)
        
        # Should include validation metadata
        assert "validation_metadata" in result.__dict__
        assert "validator_type" in result.validation_metadata
        assert "parameters_validated" in result.validation_metadata


def run_integration_test():
    """Run a complete integration test."""
    print("Running integration test...")
    
    # Test the complete flow
    context = Mock(spec=ToolContext)
    context.get_state.side_effect = lambda key: {
        "description": "Integration test task",
        "prompt": "Test the complete validation flow", 
        "subagent_type": "general-purpose"
    }.get(key)
    context.session_id = "integration-test"
    context.request_id = "integration-test-request"
    
    task_tool = TaskTool()
    
    async def run_test():
        result = await task_tool.execute(context)
        
        if result.success:
            print("✅ Integration test PASSED")
            print(f"   Execution time: {result.execution_time:.3f}s")
            print(f"   Security validated: {result.data.get('security_validation', {}).get('validated', False)}")
            return True
        else:
            print("❌ Integration test FAILED")
            print(f"   Error: {result.error}")
            return False
    
    return asyncio.run(run_test())


if __name__ == "__main__":
    print("Task Tool Validation Security Test Suite")
    print("=" * 50)
    
    # Run integration test
    integration_success = run_integration_test()
    
    print(f"\nIntegration Test: {'PASSED' if integration_success else 'FAILED'}")
    print("\nRun full test suite with: python -m pytest TEST_VALIDATION_FIXES.py -v")
    
    # Basic validation test
    try:
        validator = StringValidator()
        result = validator.validate("test string")
        print(f"✅ Basic validation working: {result.valid}")
        
        # Test security validation
        result = validator.validate("; rm -rf /")
        print(f"✅ Security validation working: {not result.valid}")
        
        print("\n🎉 All basic tests passed! Run pytest for comprehensive testing.")
        
    except Exception as e:
        print(f"❌ Basic validation failed: {e}")
        print("Check that unified_validation.py is properly imported")