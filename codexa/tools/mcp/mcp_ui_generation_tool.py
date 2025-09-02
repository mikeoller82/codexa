"""
MCP UI Generation Tool for Codexa.
"""

import logging
from typing import Set, Dict, Any
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class MCPUIGenerationTool(Tool):
    """Tool for generating UI components using MCP servers (especially Magic)."""
    
    def __init__(self):
        super().__init__()
    
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
        return set()  # Can extract description from user request
    
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
            
            # Try MCP service first if available
            if context.mcp_service and context.mcp_service.is_running:
                try:
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
                            "generation_result": generation_result,
                            "method": "mcp"
                        },
                        tool_name=self.name,
                        output=f"Generated {framework} component via MCP: {description}",
                        recommendations=[
                            "Review the generated component for your specific needs",
                            "Test the component in your application",
                            "Consider adding unit tests for the component"
                        ]
                    )
                except Exception as mcp_error:
                    # Fall back to built-in generation if MCP fails
                    self.logger.warning(f"MCP UI generation failed, falling back to built-in: {mcp_error}")
            
            # Fallback: Generate UI component using built-in capabilities
            component_code = self._generate_built_in_component(description, framework)
            
            return ToolResult.success_result(
                data={
                    "description": description,
                    "framework": framework,
                    "component_code": component_code,
                    "method": "built_in"
                },
                tool_name=self.name,
                output=f"Generated {framework} component using built-in generator: {description}",
                recommendations=[
                    "Review the generated component for your specific needs",
                    "Test the component in your application",
                    "Consider adding unit tests for the component",
                    "For advanced UI generation, consider enabling MCP servers"
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
    
    def _generate_built_in_component(self, description: str, framework: str) -> str:
        """Generate a basic UI component using built-in templates."""
        if framework.lower() == "react":
            return self._generate_react_component(description)
        elif framework.lower() == "vue":
            return self._generate_vue_component(description)
        elif framework.lower() == "angular":
            return self._generate_angular_component(description)
        else:
            # Default to React
            return self._generate_react_component(description)
    
    def _generate_react_component(self, description: str) -> str:
        """Generate a React component."""
        # Extract component name from description
        component_name = self._extract_component_name(description)
        component_lower = component_name.lower()
        
        # Build the component step by step to avoid formatting issues
        lines = [
            "import React, { useState } from 'react';",
            f"import './{component_name}.css';",
            "",
            f"interface {component_name}Props {{",
            "  // Add your props here",
            "  className?: string;",
            "  children?: React.ReactNode;",
            "}",
            "",
            f"const {component_name}: React.FC<{component_name}Props> = ({{ ",
            "  className = '', ",
            "  children,",
            "  ...props ",
            "}}) => {{",
            "  const [isActive, setIsActive] = useState(false);",
            "",
            "  const handleClick = () => {{",
            "    setIsActive(!isActive);",
            "  }};",
            "",
            "  return (",
            "    <div ",
            "      className={`" + component_lower + "-container ${className}`}",
            "      onClick={{handleClick}}",
            "      {{...props}}",
            "    >",
            "      <div className={`" + component_lower + "-content ${isActive ? 'active' : ''}`}>",
            "        {children || '" + description + "'}",
            "      </div>",
            "    </div>",
            "  );",
            "}};",
            "",
            f"export default {component_name};"
        ]
        
        return "\n".join(lines)
    
    def _generate_vue_component(self, description: str) -> str:
        """Generate a Vue component."""
        component_name = self._extract_component_name(description)
        component_lower = component_name.lower()
        
        return f'''<template>
  <div 
    :class="['{component_lower}-container', className, {{ active: isActive }}]"
    @click="handleClick"
  >
    <div class="{component_lower}-content">
      <slot>{{ '{description}' }}</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import {{ ref }} from 'vue'

interface Props {{
  className?: string
}}

const props = withDefaults(defineProps<Props>(), {{
  className: ''
}})

const isActive = ref(false)

const handleClick = () => {{
  isActive.value = !isActive.value
}}
</script>

<style scoped>
.{component_lower}-container {{
  cursor: pointer;
  transition: all 0.3s ease;
}}

.{component_lower}-container.active {{
  transform: scale(1.05);
}}

.{component_lower}-content {{
  padding: 1rem;
  border-radius: 8px;
  background-color: #f5f5f5;
}}
</style>'''
    
    def _generate_angular_component(self, description: str) -> str:
        """Generate an Angular component."""
        component_name = self._extract_component_name(description)
        component_lower = component_name.lower()
        
        return f'''import {{ Component, Input, Output, EventEmitter }} from '@angular/core';

@Component({{
  selector: 'app-{component_lower}',
  templateUrl: './{component_lower}.component.html',
  styleUrls: ['./{component_lower}.component.css']
}})
export class {component_name}Component {{
  @Input() className: string = '';
  @Output() clicked = new EventEmitter<void>();
  
  isActive: boolean = false;

  handleClick(): void {{
    this.isActive = !this.isActive;
    this.clicked.emit();
  }}
}}'''
    
    def _extract_component_name(self, description: str) -> str:
        """Extract a suitable component name from description."""
        # Clean up the description and create a component name
        words = re.findall(r'\\b\\w+\\b', description)
        if not words:
            return "CustomComponent"
        
        # Take first few words and capitalize them
        component_name = ''.join(word.capitalize() for word in words[:3])
        
        # Ensure it ends with "Component" if it doesn't already
        if not component_name.endswith('Component'):
            component_name += 'Component'
        
        return component_name