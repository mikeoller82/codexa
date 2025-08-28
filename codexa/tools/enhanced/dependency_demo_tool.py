"""
Dependency Demonstration Tool - Shows how tools can declare and coordinate dependencies
"""

from typing import List, Dict, Any
from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus, DependencyType, ToolDependency, CoordinationConfig


class DataValidatorTool(Tool):
    """Tool that validates data formats - used as a dependency by other tools"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def name(self) -> str:
        return "data_validator"
    
    @property
    def description(self) -> str:
        return "Validates data formats and structure for other tools"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def provides_capabilities(self) -> set:
        return {"data_validation", "format_checking", "structure_analysis"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        request_lower = request.lower()
        if any(word in request_lower for word in ['validate', 'check format', 'data structure']):
            return 0.8
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute data validation."""
        try:
            # Simulate data validation
            validation_results = {
                "format_valid": True,
                "structure_valid": True,
                "data_types_valid": True,
                "validation_timestamp": "2024-01-01T00:00:00Z",
                "validated_fields": ["id", "name", "email", "created_at"]
            }
            
            return ToolResult.success_result(
                data=validation_results,
                tool_name=self.name,
                output="✅ Data validation completed successfully. All formats and structures are valid."
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Data validation failed: {str(e)}",
                tool_name=self.name
            )


class DataProcessorTool(Tool):
    """Tool that processes data - depends on DataValidatorTool"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def name(self) -> str:
        return "data_processor"
    
    @property
    def description(self) -> str:
        return "Processes data after validation - demonstrates required dependencies"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def version(self) -> str:
        return "1.1.0"
    
    @property
    def dependencies(self) -> List[ToolDependency]:
        return [
            ToolDependency(
                name="data_validation",  # Capability requirement
                dependency_type=DependencyType.REQUIRED,
                version_constraint=">=1.0.0",
                condition="Must validate data before processing",
                fallback_tools=["data_validator"]
            )
        ]
    
    @property
    def coordination_config(self) -> CoordinationConfig:
        return CoordinationConfig(
            prefer_parallel=False,  # Must run after validation
            resolve_dependencies=True,
            fail_on_missing_dependencies=True
        )
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        request_lower = request.lower()
        if any(word in request_lower for word in ['process data', 'transform', 'analyze data']):
            return 0.9
        return 0.0
    
    async def coordinate_with_dependency(self, dependency_result: ToolResult, context: ToolContext) -> None:
        """Handle result from data validator."""
        if dependency_result.tool_name == "data_validator" and dependency_result.success:
            validation_data = dependency_result.data
            context.update_state("validation_results", validation_data)
            self.logger.info("Received validation results for processing")
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute data processing."""
        try:
            # Check if validation results are available
            validation_results = context.get_state("validation_results")
            if not validation_results:
                return ToolResult.error_result(
                    error="No validation results available - dependency not satisfied",
                    tool_name=self.name
                )
            
            # Process the validated data
            processing_results = {
                "processed_records": 150,
                "transformations_applied": ["normalize", "deduplicate", "enrich"],
                "processing_time": "2.3s",
                "validation_reference": validation_results.get("validation_timestamp"),
                "output_format": "JSON",
                "quality_score": 0.95
            }
            
            return ToolResult.success_result(
                data=processing_results,
                tool_name=self.name,
                output=f"📊 Data processing completed. Processed {processing_results['processed_records']} records with quality score {processing_results['quality_score']:.1%}"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Data processing failed: {str(e)}",
                tool_name=self.name
            )


class ReportGeneratorTool(Tool):
    """Tool that generates reports - has optional dependencies and conflicts"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def name(self) -> str:
        return "report_generator"
    
    @property
    def description(self) -> str:
        return "Generates reports from processed data - demonstrates optional dependencies and conflicts"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def dependencies(self) -> List[ToolDependency]:
        return [
            ToolDependency(
                name="data_processor",
                dependency_type=DependencyType.OPTIONAL,
                version_constraint=">=1.0.0",
                condition="Enhanced reports if data processing is available"
            ),
            ToolDependency(
                name="legacy_report_tool",  # Example conflict
                dependency_type=DependencyType.CONFLICT,
                condition="Cannot run with legacy reporting tools"
            )
        ]
    
    @property
    def coordination_config(self) -> CoordinationConfig:
        return CoordinationConfig(
            prefer_parallel=True,  # Can run in parallel with some tools
            continue_on_optional_failure=True,
            max_parallel_tools=2
        )
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        request_lower = request.lower()
        if any(word in request_lower for word in ['report', 'generate report', 'summary']):
            return 0.85
        return 0.0
    
    async def coordinate_with_dependency(self, dependency_result: ToolResult, context: ToolContext) -> None:
        """Handle result from data processor."""
        if dependency_result.tool_name == "data_processor" and dependency_result.success:
            processing_data = dependency_result.data
            context.update_state("processing_results", processing_data)
            self.logger.info("Received processing results for enhanced reporting")
    
    def can_run_parallel_with(self, other_tool: 'Tool') -> bool:
        """Custom parallel compatibility check."""
        # Cannot run in parallel with data processors (needs their output)
        if other_tool.name in ["data_processor", "data_validator"]:
            return False
        return super().can_run_parallel_with(other_tool)
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute report generation."""
        try:
            # Check for optional processing results
            processing_results = context.get_state("processing_results")
            
            if processing_results:
                # Enhanced report with processing data
                report_data = {
                    "report_type": "Enhanced Data Report",
                    "based_on_processing": True,
                    "records_processed": processing_results.get("processed_records", 0),
                    "quality_score": processing_results.get("quality_score", 0.0),
                    "transformations": processing_results.get("transformations_applied", []),
                    "sections": ["Executive Summary", "Data Quality", "Processing Results", "Recommendations"],
                    "generated_at": "2024-01-01T00:00:00Z"
                }
                output_msg = f"📄 Enhanced report generated with {processing_results.get('processed_records', 0)} processed records"
            else:
                # Basic report without processing data
                report_data = {
                    "report_type": "Basic Data Report",
                    "based_on_processing": False,
                    "sections": ["Basic Summary", "Raw Data Overview"],
                    "generated_at": "2024-01-01T00:00:00Z",
                    "note": "Enhanced features available with data processing"
                }
                output_msg = "📄 Basic report generated (enhanced features require data processing)"
            
            return ToolResult.success_result(
                data=report_data,
                tool_name=self.name,
                output=output_msg
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Report generation failed: {str(e)}",
                tool_name=self.name
            )


class CoordinationDemoTool(Tool):
    """Tool that demonstrates coordination capabilities"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def name(self) -> str:
        return "coordination_demo"
    
    @property
    def description(self) -> str:
        return "Demonstrates tool coordination and dependency resolution capabilities"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        request_lower = request.lower()
        if any(word in request_lower for word in ['coordination demo', 'dependency demo', 'test coordination']):
            return 0.9
        elif any(word in request_lower for word in ['coordination', 'dependencies', 'demo']):
            return 0.6
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute coordination demonstration."""
        try:
            demo_info = {
                "demo_type": "Tool Coordination System",
                "available_tools": [
                    {
                        "name": "data_validator",
                        "role": "Provides data validation capabilities",
                        "dependencies": [],
                        "provides": ["data_validation", "format_checking"]
                    },
                    {
                        "name": "data_processor", 
                        "role": "Processes validated data",
                        "dependencies": ["data_validation (required)"],
                        "coordination": "Must run after validation"
                    },
                    {
                        "name": "report_generator",
                        "role": "Generates reports from processed data",
                        "dependencies": ["data_processor (optional)"],
                        "coordination": "Can run in parallel with some tools"
                    }
                ],
                "coordination_features": [
                    "Automatic dependency resolution",
                    "Parallel execution optimization", 
                    "Conflict detection and resolution",
                    "Fallback tool support",
                    "Version constraint checking",
                    "Result coordination between tools"
                ],
                "execution_example": {
                    "request": "process data and generate report",
                    "resolved_order": ["data_validator", "data_processor", "report_generator"],
                    "execution_groups": [["data_validator"], ["data_processor"], ["report_generator"]],
                    "coordination_points": [
                        "data_processor receives validation results",
                        "report_generator receives processing results"
                    ]
                }
            }
            
            return ToolResult.success_result(
                data=demo_info,
                tool_name=self.name,
                output="🔧 Tool Coordination System Demo\n\nThe coordination system provides:\n" +
                       "• Automatic dependency resolution\n" + 
                       "• Parallel execution optimization\n" +
                       "• Inter-tool result coordination\n" +
                       "• Conflict detection and prevention\n\n" +
                       "Try: 'process data and generate report' to see coordination in action!"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Coordination demo failed: {str(e)}",
                tool_name=self.name
            )