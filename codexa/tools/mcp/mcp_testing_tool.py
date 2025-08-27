"""
MCP Testing Tool for Codexa.
"""

from typing import Set, Dict, Any, Optional
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPTestingTool(Tool):
    """Tool for running tests using MCP servers (especially Playwright)."""
    
    @property
    def name(self) -> str:
        return "mcp_testing"
    
    @property
    def description(self) -> str:
        return "Run tests using Playwright or testing servers"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"testing", "playwright", "e2e", "validation"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"test_type"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        # Only handle if MCP service is available
        if not context.mcp_service or not context.mcp_service.is_running:
            return 0.0
        
        request_lower = request.lower()
        
        # High confidence for explicit testing requests
        if any(phrase in request_lower for phrase in [
            "run tests", "test", "testing", "e2e", "end to end",
            "playwright", "automation", "validate"
        ]):
            return 0.8
        
        # Medium confidence for test-related keywords
        if any(phrase in request_lower for phrase in [
            "check", "verify", "validate", "test"
        ]) and any(word in request_lower for word in [
            "ui", "interface", "website", "app", "application"
        ]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute testing."""
        try:
            # Check MCP service availability
            if not context.mcp_service or not context.mcp_service.is_running:
                return ToolResult.error_result(
                    error="MCP service not available",
                    tool_name=self.name
                )
            
            # Get parameters from context
            test_type = context.get_state("test_type", "unit")
            target = context.get_state("target")
            
            # Try to extract from request if not in context
            if not target:
                extracted = self._extract_testing_parameters(context.user_request)
                test_type = extracted.get("test_type", test_type)
                target = extracted.get("target")
            
            # Run tests via MCP service
            test_result = await context.mcp_service.run_tests(test_type, target)
            
            # Parse test results
            success = self._parse_test_success(test_result)
            
            return ToolResult.success_result(
                data={
                    "test_type": test_type,
                    "target": target,
                    "result": test_result,
                    "success": success
                },
                tool_name=self.name,
                output=f"Tests completed: {test_type}" + (f" for {target}" if target else "") + 
                       f" - {'PASSED' if success else 'FAILED'}"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Testing failed: {str(e)}",
                tool_name=self.name
            )
    
    def _extract_testing_parameters(self, request: str) -> Dict[str, Optional[str]]:
        """Extract testing parameters from request."""
        result = {"test_type": "unit", "target": None}
        
        request_lower = request.lower()
        
        # Detect test type
        if any(word in request_lower for word in ["e2e", "end to end", "integration"]):
            result["test_type"] = "e2e"
        elif "unit" in request_lower:
            result["test_type"] = "unit"
        elif any(word in request_lower for word in ["playwright", "browser", "ui"]):
            result["test_type"] = "e2e"
        
        # Extract target
        target_patterns = [
            r'test (.+)',
            r'run tests for (.+)',
            r'testing (.+)',
            r'validate (.+)'
        ]
        
        for pattern in target_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["target"] = matches[0].strip()
                break
        
        return result
    
    def _parse_test_success(self, test_result: Any) -> bool:
        """Parse test result to determine success."""
        if isinstance(test_result, dict):
            return test_result.get("success", False)
        elif isinstance(test_result, str):
            return "passed" in test_result.lower() or "success" in test_result.lower()
        return False