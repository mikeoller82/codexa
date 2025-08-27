"""
MCP UI Generation Tool for Codexa.
"""

from typing import Set, Dict, Any
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPUIGenerationTool(Tool):
    """Tool for generating UI components using MCP servers (especially Magic)."""
    
    @property
    def name(self) -> str:
        return "mcp_ui_generation"
    
    @property
    def description(self) -> str:
        return "Generate UI components using Magic or UI generation servers"
    
    @property
    def category(self) -> str:
        return "mcp"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"ui_generation", "magic", "components", "frontend"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"description"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        # Only handle if MCP service is available
        if not context.mcp_service or not context.mcp_service.is_running:
            return 0.0
        
        request_lower = request.lower()
        
        # High confidence for explicit UI generation requests
        if any(phrase in request_lower for phrase in [
            "generate component", "create component", "ui component", "generate ui",
            "create ui", "build component", "component", "interface"
        ]):
            return 0.9
        
        # Medium confidence for UI-related keywords
        if any(phrase in request_lower for phrase in [
            "button", "form", "modal", "dialog", "input", "card",
            "navbar", "sidebar", "header", "footer", "menu"
        ]) and any(word in request_lower for word in ["create", "generate", "build"]):
            return 0.8
        
        # Low confidence for general frontend terms
        if any(word in request_lower for word in [
            "react", "vue", "angular", "jsx", "tsx", "frontend"
        ]) and any(word in request_lower for word in ["create", "generate"]):
            return 0.5
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute UI component generation."""
        try:
            # Check MCP service availability
            if not context.mcp_service or not context.mcp_service.is_running:
                return ToolResult.error_result(
                    error="MCP service not available",
                    tool_name=self.name
                )
            
            # Get parameters from context
            description = context.get_state("description")
            framework = context.get_state("framework", "react")
            
            # Try to extract from request if not in context
            if not description:
                extracted = self._extract_ui_parameters(context.user_request)
                description = extracted.get("description") or context.user_request
                framework = extracted.get("framework", framework)
            
            if not description:
                return ToolResult.error_result(
                    error="No component description specified",
                    tool_name=self.name
                )
            
            # Generate UI component via MCP service
            generation_result = await context.mcp_service.generate_ui_component(
                description, framework
            )
            
            # Extract component code
            component_code = ""
            if isinstance(generation_result, dict):
                component_code = generation_result.get("component", "")
            elif isinstance(generation_result, str):
                component_code = generation_result
            
            return ToolResult.success_result(
                data={
                    "description": description,
                    "framework": framework,
                    "component_code": component_code,
                    "generation_result": generation_result
                },
                tool_name=self.name,
                output=f"Generated {framework} component: {description}",
                recommendations=[
                    "Review the generated component for your specific needs",
                    "Test the component in your application",
                    "Consider adding unit tests for the component"
                ]
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"UI generation failed: {str(e)}",
                tool_name=self.name
            )
    
    def _extract_ui_parameters(self, request: str) -> Dict[str, str]:
        """Extract UI generation parameters from request."""
        result = {"description": "", "framework": "react"}
        
        # Extract component description
        description_patterns = [
            r'generate (.+?) component',
            r'create (.+?) component',
            r'build (.+?) component',
            r'component for (.+)',
            r'ui for (.+)',
            r'interface for (.+)'
        ]
        
        for pattern in description_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["description"] = matches[0].strip()
                break
        
        # If no specific description found, use the whole request
        if not result["description"]:
            # Remove common prefixes
            description = request
            for prefix in ["generate", "create", "build", "make"]:
                if description.lower().startswith(prefix):
                    description = description[len(prefix):].strip()
                    break
            result["description"] = description
        
        # Detect framework
        request_lower = request.lower()
        if "vue" in request_lower:
            result["framework"] = "vue"
        elif "angular" in request_lower:
            result["framework"] = "angular"
        elif "svelte" in request_lower:
            result["framework"] = "svelte"
        # Default to react
        
        return result