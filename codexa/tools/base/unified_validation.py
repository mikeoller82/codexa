"""
Unified validation framework for Codexa tools.

This module provides a comprehensive validation system that eliminates the disconnect
between Claude Code registry validation and tool context validation.
"""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Union, Callable
from enum import Enum

from .tool_interface import ToolContext


class ValidationSeverity(Enum):
    """Validation error severity levels."""
    INFO = "info"
    WARNING = "warning"  
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Validation error categories for security classification."""
    INJECTION = "injection"          # Potential code/command injection
    AUTHENTICATION = "authentication" # Auth/authorization failures  
    DATA_INTEGRITY = "data_integrity" # Data validation failures
    RESOURCE_EXHAUSTION = "resource_exhaustion" # DoS/resource issues
    INFORMATION_DISCLOSURE = "information_disclosure" # Info leaks


@dataclass
class ValidationResult:
    """Comprehensive validation result."""
    valid: bool
    parameters: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    security_issues: List[Dict[str, str]] = field(default_factory=list)
    sanitized_parameters: Dict[str, Any] = field(default_factory=dict)
    validation_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str, category: ValidationCategory = ValidationCategory.DATA_INTEGRITY,
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        """Add validation error with security categorization."""
        self.errors.append(message)
        self.security_issues.append({
            "message": message,
            "category": category.value,
            "severity": severity.value
        })
        if severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.valid = False
    
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)
    
    def get_user_friendly_error(self) -> str:
        """Get user-friendly error message without internal details."""
        if not self.errors:
            return ""
        
        # Group errors by category for better UX
        error_groups = {}
        for issue in self.security_issues:
            category = issue["category"]
            if category not in error_groups:
                error_groups[category] = []
            error_groups[category].append(issue["message"])
        
        # Return sanitized error messages
        user_errors = []
        for category, messages in error_groups.items():
            if category == ValidationCategory.DATA_INTEGRITY.value:
                user_errors.extend(messages)
            elif category == ValidationCategory.INJECTION.value:
                user_errors.append("Invalid characters detected in input")
            elif category == ValidationCategory.AUTHENTICATION.value:
                user_errors.append("Required parameters are missing or invalid")
            else:
                user_errors.append("Validation failed - please check your input")
        
        return "; ".join(user_errors[:3])  # Limit to 3 errors for UX


class ParameterValidator(ABC):
    """Abstract base class for parameter validators."""
    
    @abstractmethod
    def validate(self, value: Any, context: Optional[ToolContext] = None) -> ValidationResult:
        """Validate a parameter value."""
        pass


class StringValidator(ParameterValidator):
    """Validator for string parameters with security checks."""
    
    def __init__(self, min_length: int = 1, max_length: int = 10000, 
                 allow_empty: bool = False, pattern: Optional[str] = None,
                 forbidden_patterns: Optional[List[str]] = None):
        self.min_length = min_length
        self.max_length = max_length
        self.allow_empty = allow_empty
        self.pattern = re.compile(pattern) if pattern else None
        self.forbidden_patterns = [re.compile(p) for p in (forbidden_patterns or [])]
        
        # Default security patterns to prevent injection
        self.security_patterns = [
            re.compile(r'[;&|`$]'),  # Command injection characters
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE),  # XSS
            re.compile(r'(union|select|insert|update|delete|drop|create|alter)\s+', re.IGNORECASE),  # SQL injection
            re.compile(r'eval\s*\(|exec\s*\(|system\s*\(', re.IGNORECASE),  # Code execution
        ]
    
    def validate(self, value: Any, context: Optional[ToolContext] = None) -> ValidationResult:
        """Validate string parameter with security checks."""
        result = ValidationResult(valid=True)
        
        # Type check
        if not isinstance(value, str):
            result.add_error(f"Expected string, got {type(value).__name__}")
            return result
        
        # Empty check
        if not value.strip() and not self.allow_empty:
            result.add_error("Value cannot be empty", 
                           ValidationCategory.AUTHENTICATION,
                           ValidationSeverity.ERROR)
            return result
        
        # Length checks
        if len(value) < self.min_length:
            result.add_error(f"Value too short (minimum {self.min_length} characters)")
            return result
        
        if len(value) > self.max_length:
            result.add_error(f"Value too long (maximum {self.max_length} characters)",
                           ValidationCategory.RESOURCE_EXHAUSTION,
                           ValidationSeverity.WARNING)
            # Truncate but don't fail
            value = value[:self.max_length]
            result.add_warning(f"Value truncated to {self.max_length} characters")
        
        # Pattern validation
        if self.pattern and not self.pattern.match(value):
            result.add_error("Value does not match required pattern")
            return result
        
        # Security pattern checks
        for pattern in self.security_patterns:
            if pattern.search(value):
                result.add_error("Input contains potentially dangerous content",
                               ValidationCategory.INJECTION,
                               ValidationSeverity.CRITICAL)
                return result
        
        # Forbidden pattern checks  
        for pattern in self.forbidden_patterns:
            if pattern.search(value):
                result.add_error("Input contains forbidden content")
                return result
        
        # Sanitize the parameter
        sanitized = self._sanitize_string(value)
        result.sanitized_parameters["sanitized_value"] = sanitized
        result.parameters["original_value"] = value
        result.valid = True
        
        return result
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string by removing/escaping dangerous characters."""
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        
        # Escape shell metacharacters for safety
        shell_chars = ['&', '|', ';', '`', '$', '(', ')', '<', '>', '"', "'"]
        for char in shell_chars:
            sanitized = sanitized.replace(char, f'\\{char}')
        
        return sanitized.strip()


class EnumValidator(ParameterValidator):
    """Validator for enum/choice parameters."""
    
    def __init__(self, allowed_values: Set[str], case_sensitive: bool = True):
        self.allowed_values = allowed_values
        self.case_sensitive = case_sensitive
        if not case_sensitive:
            self.allowed_values = {v.lower() for v in allowed_values}
    
    def validate(self, value: Any, context: Optional[ToolContext] = None) -> ValidationResult:
        """Validate enum parameter."""
        result = ValidationResult(valid=True)
        
        if not isinstance(value, str):
            result.add_error(f"Expected string, got {type(value).__name__}")
            return result
        
        check_value = value if self.case_sensitive else value.lower()
        
        if check_value not in self.allowed_values:
            result.add_error(f"Invalid value '{value}'. Allowed: {', '.join(sorted(self.allowed_values))}")
            return result
        
        result.parameters["validated_value"] = value
        result.valid = True
        return result


class UnifiedValidator:
    """Unified validation system for all Codexa tools."""
    
    def __init__(self):
        self.logger = logging.getLogger("codexa.validation")
        self.tool_validators: Dict[str, Dict[str, ParameterValidator]] = {}
        self._register_default_validators()
    
    def _register_default_validators(self):
        """Register default validators for Claude Code tools."""
        
        # Task tool validators
        self.tool_validators["Task"] = {
            "description": StringValidator(min_length=3, max_length=100),
            "prompt": StringValidator(min_length=5, max_length=5000),
            "subagent_type": EnumValidator({
                "general-purpose", "statusline-setup", "output-style-setup"
            })
        }
        
        # Bash tool validators
        self.tool_validators["Bash"] = {
            "command": StringValidator(
                min_length=1, 
                max_length=2000,
                forbidden_patterns=[
                    r'rm\s+-rf\s+/', # Prevent dangerous deletions
                    r':\s*\(\)\s*\{[^}]*\}\s*;',  # Fork bombs
                    r'while\s+true',  # Infinite loops
                ]
            ),
            "description": StringValidator(max_length=200, allow_empty=True)
        }
        
        # Write tool validators
        self.tool_validators["Write"] = {
            "file_path": StringValidator(min_length=1, max_length=500),
            "content": StringValidator(min_length=0, max_length=100000, allow_empty=True)  # Allow empty content
        }
        
        # Read tool validators
        self.tool_validators["Read"] = {
            "file_path": StringValidator(min_length=1, max_length=500),
        }
        
        # Add more tool validators as needed...
    
    def register_tool_validator(self, tool_name: str, 
                              parameter_validators: Dict[str, ParameterValidator]):
        """Register validators for a specific tool."""
        self.tool_validators[tool_name] = parameter_validators
    
    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any],
                                context: Optional[ToolContext] = None) -> ValidationResult:
        """Validate parameters for a specific tool."""
        result = ValidationResult(valid=True)
        
        if tool_name not in self.tool_validators:
            # No specific validators - perform basic validation
            result = self._basic_validation(parameters)
            result.validation_metadata["validator_type"] = "basic"
            return result
        
        validators = self.tool_validators[tool_name]
        result.validation_metadata["validator_type"] = "specific"
        
        # Validate each parameter
        for param_name, validator in validators.items():
            if param_name in parameters:
                param_result = validator.validate(parameters[param_name], context)
                
                # Merge results
                if not param_result.valid:
                    result.valid = False
                    result.errors.extend(param_result.errors)
                    result.security_issues.extend(param_result.security_issues)
                
                result.warnings.extend(param_result.warnings)
                
                # Use sanitized value if available
                if param_result.sanitized_parameters:
                    sanitized_key = f"sanitized_{param_name}"
                    result.sanitized_parameters[sanitized_key] = param_result.sanitized_parameters.get("sanitized_value", parameters[param_name])
                else:
                    result.sanitized_parameters[param_name] = parameters[param_name]
                
                result.parameters[param_name] = param_result.parameters.get("validated_value", parameters[param_name])
            else:
                # Missing required parameter
                result.add_error(f"Missing required parameter: {param_name}",
                               ValidationCategory.AUTHENTICATION,
                               ValidationSeverity.ERROR)
        
        # Check for unexpected parameters
        unexpected = set(parameters.keys()) - set(validators.keys())
        if unexpected:
            result.add_warning(f"Unexpected parameters: {', '.join(unexpected)}")
        
        result.validation_metadata["parameters_validated"] = len(validators)
        result.validation_metadata["security_checks_performed"] = len([
            issue for issue in result.security_issues 
            if issue["category"] in [ValidationCategory.INJECTION.value]
        ])
        
        return result
    
    def _basic_validation(self, parameters: Dict[str, Any]) -> ValidationResult:
        """Basic validation for tools without specific validators."""
        result = ValidationResult(valid=True)
        result.parameters = parameters.copy()
        
        for key, value in parameters.items():
            if value is None:
                result.add_error(f"Parameter '{key}' cannot be None")
            elif isinstance(value, str) and not value.strip():
                result.add_warning(f"Parameter '{key}' is empty")
            
            # Basic security check for strings
            if isinstance(value, str) and len(value) > 10000:
                result.add_error(f"Parameter '{key}' is too long (>10000 chars)",
                               ValidationCategory.RESOURCE_EXHAUSTION)
        
        return result
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation system statistics."""
        return {
            "registered_tools": len(self.tool_validators),
            "total_validators": sum(len(v) for v in self.tool_validators.values()),
            "security_patterns": len(StringValidator().__dict__.get('security_patterns', [])),
        }


# Global unified validator instance
unified_validator = UnifiedValidator()