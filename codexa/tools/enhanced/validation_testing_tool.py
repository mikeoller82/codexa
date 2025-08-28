"""
Validation and Testing Tool - Provides comprehensive tool validation and testing capabilities
"""

from typing import Dict, List, Any, Optional
import asyncio

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus
from ..base.tool_validator import ToolValidator, ValidationSeverity, ValidationCategory
from ..base.tool_testing import ToolTester, TestType


class ValidationTestingTool(Tool):
    """Tool for comprehensive validation and testing of other tools"""
    
    def __init__(self):
        super().__init__()
        self.validator = ToolValidator()
        self.tester = ToolTester(self.validator)
    
    @property
    def name(self) -> str:
        return "validation_testing"
    
    @property
    def description(self) -> str:
        return "Comprehensive tool validation and testing framework"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def provides_capabilities(self) -> set:
        return {"validation", "testing", "quality_assurance", "tool_analysis"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the validation/testing request."""
        request_lower = request.lower()
        
        # High confidence for explicit validation/testing requests
        if any(word in request_lower for word in [
            'validate', 'test', 'check', 'verify', 'quality',
            'validation', 'testing', 'qa', 'quality assurance'
        ]):
            return 0.9
        
        # Medium confidence for analysis requests
        if any(word in request_lower for word in [
            'analyze', 'inspect', 'review', 'audit', 'assess'
        ]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute validation and testing operations."""
        try:
            request = context.user_request or ""
            request_lower = request.lower()
            
            # Parse the request to determine what to do
            if "validate" in request_lower:
                return await self._handle_validation_request(request, context)
            elif "test" in request_lower:
                return await self._handle_testing_request(request, context)
            elif "analyze" in request_lower or "report" in request_lower:
                return await self._handle_analysis_request(request, context)
            else:
                return await self._handle_general_request(request, context)
                
        except Exception as e:
            return ToolResult.error_result(
                error=f"Validation/testing failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _handle_validation_request(self, request: str, context: ToolContext) -> ToolResult:
        """Handle tool validation requests."""
        # For now, return validation capabilities info
        validation_info = {
            "validation_framework": "Tool Validation System",
            "capabilities": [
                "Interface compliance checking",
                "Dependency validation", 
                "Runtime behavior testing",
                "Performance analysis",
                "Security assessment",
                "Compatibility verification"
            ],
            "validation_categories": [cat.value for cat in ValidationCategory],
            "severity_levels": [sev.value for sev in ValidationSeverity],
            "features": {
                "automatic_validation": True,
                "custom_validation_rules": True,
                "batch_validation": True,
                "validation_reports": True,
                "integration_with_testing": True
            },
            "usage": {
                "validate_single_tool": "validator.validate_tool(tool, context)",
                "batch_validation": "validator.validate_multiple_tools(tools)",
                "custom_rules": "validator.add_custom_rule(rule)"
            }
        }
        
        return ToolResult.success_result(
            data=validation_info,
            tool_name=self.name,
            output="🔍 **Tool Validation Framework**\n\n" +
                   "Comprehensive validation system providing:\n" +
                   "• Interface compliance checking\n" +
                   "• Dependency validation and analysis\n" +
                   "• Runtime behavior verification\n" +
                   "• Performance and security assessment\n" +
                   "• Automated report generation\n\n" +
                   "Ready to validate tools across multiple quality dimensions!"
        )
    
    async def _handle_testing_request(self, request: str, context: ToolContext) -> ToolResult:
        """Handle tool testing requests."""
        testing_info = {
            "testing_framework": "Tool Testing System",
            "test_types": [test_type.value for test_type in TestType],
            "capabilities": [
                "Automated test case generation",
                "Unit and integration testing",
                "Performance benchmarking",
                "Stress testing",
                "Security testing",
                "Compatibility testing"
            ],
            "features": {
                "test_suite_management": True,
                "automated_test_discovery": True,
                "parallel_test_execution": True,
                "performance_benchmarking": True,
                "test_reporting": True,
                "continuous_testing": True
            },
            "test_suite_structure": {
                "basic_tests": [
                    "Interface compliance",
                    "Basic execution",
                    "Return value validation",
                    "Property verification",
                    "Performance threshold"
                ],
                "advanced_tests": [
                    "Dependency handling",
                    "Error conditions",
                    "Edge cases",
                    "Resource usage",
                    "Concurrency safety"
                ]
            },
            "usage": {
                "create_test_suite": "tester.create_test_suite(name, tool_name)",
                "add_test_case": "tester.add_test_case(suite, name, type, func)",
                "run_tests": "tester.run_test_suite(suite_name, tool, context)",
                "benchmark": "tester.run_benchmark(tool, iterations)"
            }
        }
        
        return ToolResult.success_result(
            data=testing_info,
            tool_name=self.name,
            output="🧪 **Tool Testing Framework**\n\n" +
                   "Comprehensive testing system offering:\n" +
                   "• Automated test case generation\n" +
                   "• Multiple test types (unit, integration, performance)\n" +
                   "• Test suite management and execution\n" +
                   "• Performance benchmarking\n" +
                   "• Detailed test reporting and analytics\n\n" +
                   "Ready to ensure tool quality and reliability!"
        )
    
    async def _handle_analysis_request(self, request: str, context: ToolContext) -> ToolResult:
        """Handle analysis and reporting requests."""
        # Get current statistics
        validation_stats = self.validator.get_validation_summary()
        testing_stats = self.tester.get_testing_stats()
        
        analysis_info = {
            "analysis_framework": "Tool Quality Analysis System",
            "current_statistics": {
                "validation": validation_stats,
                "testing": testing_stats
            },
            "analysis_capabilities": [
                "Quality score calculation",
                "Trend analysis",
                "Comparative assessment", 
                "Risk analysis",
                "Performance profiling",
                "Dependency analysis"
            ],
            "reporting_features": [
                "JSON export",
                "Detailed validation reports",
                "Test execution summaries", 
                "Performance benchmarks",
                "Quality dashboards",
                "Historical tracking"
            ],
            "quality_metrics": {
                "validation_score": "0.0 - 1.0 based on validation issues",
                "test_success_rate": "Percentage of passed tests",
                "performance_score": "Based on execution time benchmarks",
                "dependency_health": "Dependency resolution success rate",
                "overall_quality": "Composite quality score"
            }
        }
        
        return ToolResult.success_result(
            data=analysis_info,
            tool_name=self.name,
            output="📊 **Tool Quality Analysis System**\n\n" +
                   f"Current Status:\n" +
                   f"• Tools validated: {validation_stats['tools_validated']}\n" +
                   f"• Tools tested: {testing_stats['tools_tested']}\n" +
                   f"• Average validation score: {validation_stats['average_validation_score']:.2f}\n" +
                   f"• Overall test success rate: {testing_stats['overall_success_rate']:.1%}\n\n" +
                   "Providing comprehensive quality analysis and reporting!"
        )
    
    async def _handle_general_request(self, request: str, context: ToolContext) -> ToolResult:
        """Handle general validation/testing information requests."""
        framework_info = {
            "framework": "Codexa Tool Validation & Testing Framework",
            "version": self.version,
            "components": {
                "validator": {
                    "purpose": "Comprehensive tool validation",
                    "categories": len(ValidationCategory),
                    "severity_levels": len(ValidationSeverity),
                    "validations_performed": self.validator.get_validation_summary()["validations_performed"]
                },
                "tester": {
                    "purpose": "Automated tool testing",
                    "test_types": len(TestType),
                    "test_suites": len(self.tester._test_suites),
                    "tests_executed": self.tester._tests_executed
                }
            },
            "key_features": [
                "🔍 Comprehensive validation across multiple quality dimensions",
                "🧪 Automated testing with multiple test types",
                "📊 Performance benchmarking and analysis", 
                "🛡️ Security and compatibility assessment",
                "📋 Detailed reporting and analytics",
                "🔗 Integration with tool coordination system"
            ],
            "workflow": [
                "1. Tool Registration: Tools are registered in the system",
                "2. Validation: Comprehensive quality validation",
                "3. Testing: Automated test suite execution", 
                "4. Analysis: Performance and behavior analysis",
                "5. Reporting: Generate quality reports",
                "6. Continuous Monitoring: Ongoing quality assurance"
            ]
        }
        
        return ToolResult.success_result(
            data=framework_info,
            tool_name=self.name,
            output="🛠️ **Codexa Tool Validation & Testing Framework**\n\n" +
                   "Comprehensive quality assurance system providing:\n\n" +
                   "**Validation Framework:**\n" +
                   "• Interface compliance checking\n" +
                   "• Dependency validation\n" +
                   "• Security and compatibility assessment\n\n" +
                   "**Testing Framework:**\n" +
                   "• Automated test generation\n" +
                   "• Performance benchmarking\n" +
                   "• Comprehensive test reporting\n\n" +
                   "**Quality Analysis:**\n" +
                   "• Quality scoring and metrics\n" +
                   "• Trend analysis and monitoring\n" +
                   "• Detailed reporting and dashboards\n\n" +
                   "Ready to ensure the highest quality standards for your tools!"
        )
    
    async def validate_tool_by_name(self, tool_name: str, tool_manager) -> Optional[ToolResult]:
        """Validate a specific tool by name."""
        try:
            # Get tool from registry
            tool = tool_manager.registry.get_tool(tool_name)
            if not tool:
                return ToolResult.error_result(
                    error=f"Tool '{tool_name}' not found in registry",
                    tool_name=self.name
                )
            
            # Create context for validation
            context = ToolContext(
                current_path="/tmp",
                user_request=f"validate {tool_name}"
            )
            
            # Perform validation
            validation_report = await self.validator.validate_tool(tool, context)
            
            # Export report
            report_data = self.validator.export_report(validation_report)
            
            return ToolResult.success_result(
                data=report_data,
                tool_name=self.name,
                output=f"✅ Validation completed for '{tool_name}'\n\n" +
                       f"Score: {validation_report.get_score():.2f}/1.0\n" +
                       f"Issues found: {len(validation_report.issues)}\n" +
                       f"Execution time: {validation_report.execution_time:.3f}s\n\n" +
                       ("🎉 Tool passed validation!" if not validation_report.has_errors 
                        else "⚠️ Tool has validation issues that need attention.")
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Tool validation failed: {str(e)}",
                tool_name=self.name
            )
    
    async def test_tool_by_name(self, tool_name: str, tool_manager) -> Optional[ToolResult]:
        """Test a specific tool by name."""
        try:
            # Get tool from registry  
            tool = tool_manager.registry.get_tool(tool_name)
            if not tool:
                return ToolResult.error_result(
                    error=f"Tool '{tool_name}' not found in registry",
                    tool_name=self.name
                )
            
            # Create basic test suite
            suite_name = self.tester.create_basic_test_suite(tool)
            
            # Create context for testing
            context = ToolContext(
                current_path="/tmp",
                user_request=f"test {tool_name}"
            )
            
            # Run test suite
            test_result = await self.tester.run_test_suite(suite_name, tool, context)
            
            # Generate report
            report_data = self.tester.generate_test_report(test_result)
            
            return ToolResult.success_result(
                data=report_data,
                tool_name=self.name,
                output=f"🧪 Testing completed for '{tool_name}'\n\n" +
                       f"Tests passed: {test_result.passed_tests}/{test_result.total_tests}\n" +
                       f"Success rate: {test_result.success_rate:.1%}\n" +
                       f"Execution time: {test_result.execution_time:.3f}s\n\n" +
                       ("🎉 All tests passed!" if test_result.success_rate == 1.0
                        else f"⚠️ {test_result.failed_tests} test(s) failed.")
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Tool testing failed: {str(e)}",
                tool_name=self.name
            )