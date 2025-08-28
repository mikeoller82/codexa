"""
Tool Validation Framework for Codexa.

Provides comprehensive validation for tool implementations, dependencies,
and runtime behavior.
"""

import asyncio
import inspect
from typing import Dict, List, Set, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
from enum import Enum

from .tool_interface import Tool, ToolResult, ToolContext, ToolStatus, DependencyType, ToolDependency


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Validation categories."""
    INTERFACE = "interface"
    DEPENDENCIES = "dependencies"
    BEHAVIOR = "behavior"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    
    severity: ValidationSeverity
    category: ValidationCategory
    message: str
    tool_name: str
    details: Optional[str] = None
    suggestion: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        severity_icon = {
            ValidationSeverity.INFO: "ℹ️",
            ValidationSeverity.WARNING: "⚠️", 
            ValidationSeverity.ERROR: "❌",
            ValidationSeverity.CRITICAL: "🚨"
        }
        
        return f"{severity_icon[self.severity]} {self.tool_name}: {self.message}"


@dataclass
class ValidationReport:
    """Comprehensive validation report for a tool."""
    
    tool_name: str
    version: str
    timestamp: datetime
    issues: List[ValidationIssue] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    
    @property
    def has_errors(self) -> bool:
        """Check if report has error-level issues."""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                  for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if report has warning-level issues."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)
    
    @property
    def severity_counts(self) -> Dict[ValidationSeverity, int]:
        """Get count of issues by severity."""
        counts = {severity: 0 for severity in ValidationSeverity}
        for issue in self.issues:
            counts[issue.severity] += 1
        return counts
    
    @property
    def category_counts(self) -> Dict[ValidationCategory, int]:
        """Get count of issues by category."""
        counts = {category: 0 for category in ValidationCategory}
        for issue in self.issues:
            counts[issue.category] += 1
        return counts
    
    def get_score(self) -> float:
        """Calculate validation score (0.0 to 1.0)."""
        if not self.issues:
            return 1.0
        
        # Weighted scoring
        severity_weights = {
            ValidationSeverity.INFO: 0.1,
            ValidationSeverity.WARNING: 0.3,
            ValidationSeverity.ERROR: 0.7,
            ValidationSeverity.CRITICAL: 1.0
        }
        
        total_weight = sum(severity_weights[issue.severity] for issue in self.issues)
        max_possible_weight = len(self.issues) * max(severity_weights.values())
        
        return max(0.0, 1.0 - (total_weight / max_possible_weight))


class ToolValidator:
    """
    Comprehensive tool validation framework.
    
    Validates tools across multiple dimensions:
    - Interface compliance
    - Dependency correctness
    - Runtime behavior
    - Performance characteristics
    - Security considerations
    """
    
    def __init__(self):
        """Initialize tool validator."""
        self.logger = logging.getLogger("codexa.tools.validator")
        
        # Validation statistics
        self._validations_performed = 0
        self._tools_validated = set()
        self._validation_history: List[ValidationReport] = []
        
        self.logger.info("Tool validator initialized")
    
    async def validate_tool(self, 
                          tool: Tool, 
                          context: Optional[ToolContext] = None,
                          include_runtime_tests: bool = True,
                          include_performance_tests: bool = False) -> ValidationReport:
        """
        Perform comprehensive validation of a tool.
        
        Args:
            tool: Tool instance to validate
            context: Optional execution context for runtime tests
            include_runtime_tests: Whether to perform runtime behavior tests
            include_performance_tests: Whether to perform performance tests
            
        Returns:
            Validation report with all findings
        """
        start_time = datetime.now()
        self._validations_performed += 1
        self._tools_validated.add(tool.name)
        
        report = ValidationReport(
            tool_name=tool.name,
            version=tool.version,
            timestamp=start_time
        )
        
        try:
            self.logger.info(f"Validating tool: {tool.name}")
            
            # 1. Interface validation
            await self._validate_interface(tool, report)
            
            # 2. Dependency validation
            await self._validate_dependencies(tool, report)
            
            # 3. Configuration validation
            await self._validate_configuration(tool, report)
            
            # 4. Runtime behavior validation (if requested)
            if include_runtime_tests and context:
                await self._validate_runtime_behavior(tool, context, report)
            
            # 5. Performance validation (if requested)
            if include_performance_tests and context:
                await self._validate_performance(tool, context, report)
            
            # 6. Security validation
            await self._validate_security(tool, report)
            
            # 7. Compatibility validation
            await self._validate_compatibility(tool, report)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            report.execution_time = execution_time
            
            self._validation_history.append(report)
            
            score = report.get_score()
            self.logger.info(f"Tool {tool.name} validation complete: "
                           f"score {score:.2f}, "
                           f"{len(report.issues)} issues, "
                           f"{execution_time:.3f}s")
            
            return report
            
        except Exception as e:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category=ValidationCategory.INTERFACE,
                message=f"Validation failed: {str(e)}",
                tool_name=tool.name,
                details=f"Exception during validation: {type(e).__name__}"
            ))
            
            execution_time = (datetime.now() - start_time).total_seconds()
            report.execution_time = execution_time
            
            self.logger.error(f"Tool validation failed for {tool.name}: {e}")
            return report
    
    async def _validate_interface(self, tool: Tool, report: ValidationReport) -> None:
        """Validate tool interface compliance."""
        # Check required properties
        required_properties = ['name', 'description', 'category', 'version']
        for prop in required_properties:
            try:
                value = getattr(tool, prop)
                if not value or (isinstance(value, str) and not value.strip()):
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.INTERFACE,
                        message=f"Required property '{prop}' is empty or None",
                        tool_name=tool.name,
                        suggestion=f"Implement the {prop} property with a meaningful value"
                    ))
                else:
                    report.passed_checks.append(f"Property {prop} is valid")
            except AttributeError:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.INTERFACE,
                    message=f"Missing required property: {prop}",
                    tool_name=tool.name,
                    suggestion=f"Add @property {prop} to your tool class"
                ))
        
        # Check tool name format
        if hasattr(tool, 'name') and tool.name:
            if not tool.name.replace('_', '').replace('-', '').isalnum():
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.INTERFACE,
                    message="Tool name contains special characters",
                    tool_name=tool.name,
                    details=f"Name: '{tool.name}'",
                    suggestion="Use only letters, numbers, hyphens, and underscores"
                ))
            else:
                report.passed_checks.append("Tool name format is valid")
        
        # Check execute method
        if hasattr(tool, 'execute'):
            if not asyncio.iscoroutinefunction(tool.execute):
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INTERFACE,
                    message="Execute method is not async",
                    tool_name=tool.name,
                    suggestion="Make execute method async: async def execute(self, context)"
                ))
            else:
                report.passed_checks.append("Execute method is properly async")
        else:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category=ValidationCategory.INTERFACE,
                message="Missing execute method",
                tool_name=tool.name,
                suggestion="Implement async def execute(self, context: ToolContext) -> ToolResult"
            ))
        
        # Check can_handle_request method
        if hasattr(tool, 'can_handle_request'):
            sig = inspect.signature(tool.can_handle_request)
            if len(sig.parameters) != 3:  # self, request, context
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.INTERFACE,
                    message="can_handle_request method has unexpected signature",
                    tool_name=tool.name,
                    suggestion="Expected: def can_handle_request(self, request: str, context: ToolContext) -> float"
                ))
            else:
                report.passed_checks.append("can_handle_request signature is valid")
        
        # Check version format
        if hasattr(tool, 'version') and tool.version:
            try:
                parts = tool.version.split('.')
                if len(parts) not in [2, 3] or not all(part.isdigit() for part in parts):
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.INTERFACE,
                        message="Version format should follow semantic versioning",
                        tool_name=tool.name,
                        details=f"Current version: {tool.version}",
                        suggestion="Use format: major.minor.patch (e.g., '1.2.3')"
                    ))
                else:
                    report.passed_checks.append("Version format is valid")
            except Exception:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.INTERFACE,
                    message="Invalid version format",
                    tool_name=tool.name,
                    suggestion="Use semantic versioning format: major.minor.patch"
                ))
    
    async def _validate_dependencies(self, tool: Tool, report: ValidationReport) -> None:
        """Validate tool dependencies."""
        if hasattr(tool, 'dependencies'):
            dependencies = tool.dependencies
            
            if dependencies:
                # Check dependency format
                for i, dep in enumerate(dependencies):
                    if not isinstance(dep, ToolDependency):
                        report.issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.DEPENDENCIES,
                            message=f"Dependency {i} is not a ToolDependency instance",
                            tool_name=tool.name,
                            suggestion="Use ToolDependency dataclass for all dependencies"
                        ))
                        continue
                    
                    # Check dependency name
                    if not dep.name or not dep.name.strip():
                        report.issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.DEPENDENCIES,
                            message=f"Dependency {i} has empty name",
                            tool_name=tool.name
                        ))
                    
                    # Check version constraint format
                    if dep.version_constraint:
                        valid_prefixes = ['>=', '<=', '>', '<', '==', '~']
                        if not any(dep.version_constraint.startswith(prefix) for prefix in valid_prefixes):
                            report.issues.append(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                category=ValidationCategory.DEPENDENCIES,
                                message=f"Dependency '{dep.name}' has unusual version constraint",
                                tool_name=tool.name,
                                details=f"Constraint: {dep.version_constraint}",
                                suggestion="Use standard operators: >=, <=, >, <, ==, ~"
                            ))
                    
                    # Check for circular dependencies (basic check)
                    if dep.name == tool.name:
                        report.issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.DEPENDENCIES,
                            message="Tool depends on itself",
                            tool_name=tool.name,
                            details=f"Circular dependency: {dep.name}"
                        ))
                
                report.passed_checks.append(f"Processed {len(dependencies)} dependencies")
            else:
                report.passed_checks.append("No dependencies to validate")
        
        # Check legacy dependencies for compatibility
        if hasattr(tool, 'legacy_dependencies'):
            legacy_deps = tool.legacy_dependencies
            if legacy_deps:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category=ValidationCategory.DEPENDENCIES,
                    message="Tool uses legacy dependency format",
                    tool_name=tool.name,
                    details=f"Legacy dependencies: {list(legacy_deps)}",
                    suggestion="Consider migrating to new ToolDependency format"
                ))
    
    async def _validate_configuration(self, tool: Tool, report: ValidationReport) -> None:
        """Validate tool configuration."""
        if hasattr(tool, 'coordination_config'):
            config = tool.coordination_config
            
            # Validate timeout settings
            if hasattr(config, 'timeout_multiplier') and config.timeout_multiplier <= 0:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INTERFACE,
                    message="Invalid timeout multiplier",
                    tool_name=tool.name,
                    details=f"Value: {config.timeout_multiplier}",
                    suggestion="Timeout multiplier must be positive"
                ))
            
            # Validate parallel settings
            if hasattr(config, 'max_parallel_tools') and config.max_parallel_tools < 1:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INTERFACE,
                    message="Invalid max_parallel_tools setting",
                    tool_name=tool.name,
                    details=f"Value: {config.max_parallel_tools}",
                    suggestion="max_parallel_tools must be at least 1"
                ))
            
            report.passed_checks.append("Configuration validation completed")
    
    async def _validate_runtime_behavior(self, tool: Tool, context: ToolContext, report: ValidationReport) -> None:
        """Validate tool runtime behavior."""
        try:
            # Test basic execution
            test_context = ToolContext(
                current_path=context.current_path or "/tmp",
                user_request="validation test"
            )
            
            # Test can_handle_request
            try:
                confidence = tool.can_handle_request("test request", test_context)
                if not isinstance(confidence, (int, float)):
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.BEHAVIOR,
                        message="can_handle_request returns non-numeric value",
                        tool_name=tool.name,
                        details=f"Returned: {type(confidence).__name__}"
                    ))
                elif not 0.0 <= confidence <= 1.0:
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.BEHAVIOR,
                        message="can_handle_request returns value outside [0.0, 1.0] range",
                        tool_name=tool.name,
                        details=f"Value: {confidence}"
                    ))
                else:
                    report.passed_checks.append("can_handle_request returns valid confidence")
            except Exception as e:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.BEHAVIOR,
                    message="can_handle_request method throws exception",
                    tool_name=tool.name,
                    details=str(e)
                ))
            
            # Test safe_execute with timeout
            try:
                result = await asyncio.wait_for(
                    tool.safe_execute(test_context),
                    timeout=30.0  # Generous timeout for validation
                )
                
                if not isinstance(result, ToolResult):
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.BEHAVIOR,
                        message="safe_execute does not return ToolResult",
                        tool_name=tool.name,
                        details=f"Returned: {type(result).__name__}"
                    ))
                else:
                    report.passed_checks.append("safe_execute returns ToolResult")
                    
                    # Validate result structure
                    if not hasattr(result, 'success'):
                        report.issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.BEHAVIOR,
                            message="ToolResult missing 'success' attribute",
                            tool_name=tool.name
                        ))
                    
                    if result.tool_name != tool.name:
                        report.issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category=ValidationCategory.BEHAVIOR,
                            message="ToolResult tool_name doesn't match actual tool",
                            tool_name=tool.name,
                            details=f"Result tool_name: {result.tool_name}"
                        ))
            
            except asyncio.TimeoutError:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.PERFORMANCE,
                    message="Tool execution timeout during validation",
                    tool_name=tool.name,
                    details="Execution took longer than 30 seconds"
                ))
            
            except Exception as e:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.BEHAVIOR,
                    message="Tool execution failed during validation",
                    tool_name=tool.name,
                    details=str(e)
                ))
        
        except Exception as e:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.BEHAVIOR,
                message="Runtime behavior validation failed",
                tool_name=tool.name,
                details=str(e)
            ))
    
    async def _validate_performance(self, tool: Tool, context: ToolContext, report: ValidationReport) -> None:
        """Validate tool performance characteristics."""
        try:
            # Performance baseline test
            test_context = ToolContext(
                current_path=context.current_path or "/tmp",
                user_request="performance test"
            )
            
            # Measure execution time
            start_time = datetime.now()
            result = await tool.safe_execute(test_context)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Check for reasonable execution time (configurable threshold)
            if execution_time > 10.0:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.PERFORMANCE,
                    message="Tool execution time exceeds recommended threshold",
                    tool_name=tool.name,
                    details=f"Execution time: {execution_time:.3f}s",
                    suggestion="Consider optimizing tool performance"
                ))
            else:
                report.passed_checks.append(f"Performance test passed ({execution_time:.3f}s)")
            
            # Memory usage check (if possible)
            # This would require additional tooling in a production environment
            
        except Exception as e:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.PERFORMANCE,
                message="Performance validation failed",
                tool_name=tool.name,
                details=str(e)
            ))
    
    async def _validate_security(self, tool: Tool, report: ValidationReport) -> None:
        """Validate tool security considerations."""
        # Check for potential security issues in tool code
        tool_code = inspect.getsource(tool.__class__)
        
        # Basic security checks
        security_patterns = {
            'eval(': 'Use of eval() function detected',
            'exec(': 'Use of exec() function detected',
            'subprocess.': 'Direct subprocess usage detected',
            'os.system': 'Use of os.system() detected',
            '__import__': 'Dynamic import usage detected'
        }
        
        for pattern, message in security_patterns.items():
            if pattern in tool_code:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.SECURITY,
                    message=message,
                    tool_name=tool.name,
                    suggestion="Ensure secure usage and input validation"
                ))
        
        if not any(pattern in tool_code for pattern in security_patterns.keys()):
            report.passed_checks.append("No obvious security anti-patterns detected")
    
    async def _validate_compatibility(self, tool: Tool, report: ValidationReport) -> None:
        """Validate tool compatibility considerations."""
        # Check Python version compatibility
        if hasattr(tool, '__annotations__'):
            # Tool uses type annotations, good for modern Python
            report.passed_checks.append("Tool uses type annotations")
        
        # Check for async/await usage
        if hasattr(tool, 'execute') and asyncio.iscoroutinefunction(tool.execute):
            report.passed_checks.append("Tool properly implements async execution")
        
        # Check for proper inheritance
        if not isinstance(tool, Tool):
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPATIBILITY,
                message="Tool does not inherit from base Tool class",
                tool_name=tool.name
            ))
        else:
            report.passed_checks.append("Tool properly inherits from base Tool class")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation activities."""
        total_issues = sum(len(report.issues) for report in self._validation_history)
        avg_score = sum(report.get_score() for report in self._validation_history) / max(1, len(self._validation_history))
        
        return {
            "validations_performed": self._validations_performed,
            "tools_validated": len(self._tools_validated),
            "total_issues_found": total_issues,
            "average_validation_score": avg_score,
            "validation_history_size": len(self._validation_history)
        }
    
    def export_report(self, report: ValidationReport, format: str = "json") -> Union[Dict[str, Any], str]:
        """Export validation report in specified format."""
        if format.lower() == "json":
            return {
                "tool_name": report.tool_name,
                "version": report.version,
                "timestamp": report.timestamp.isoformat(),
                "validation_score": report.get_score(),
                "execution_time": report.execution_time,
                "issues": [
                    {
                        "severity": issue.severity.value,
                        "category": issue.category.value,
                        "message": issue.message,
                        "details": issue.details,
                        "suggestion": issue.suggestion,
                        "timestamp": issue.timestamp.isoformat()
                    }
                    for issue in report.issues
                ],
                "passed_checks": report.passed_checks,
                "summary": {
                    "total_issues": len(report.issues),
                    "severity_counts": {k.value: v for k, v in report.severity_counts.items()},
                    "category_counts": {k.value: v for k, v in report.category_counts.items()},
                    "has_errors": report.has_errors,
                    "has_warnings": report.has_warnings
                }
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")