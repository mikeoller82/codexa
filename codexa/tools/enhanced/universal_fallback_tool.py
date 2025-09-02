"""
Universal Fallback Tool - Ensures all requests have at least one tool available.

This tool serves as a safety net to prevent "no suitable tools found" errors
by providing a low-confidence match for any request that doesn't match other tools.
"""

import logging
from typing import Dict, Any, List
from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority


class UniversalFallbackTool(Tool):
    """
    Universal fallback tool that can handle any request with low confidence.
    
    This tool ensures that the system never fails with "no suitable tools found"
    by providing a catch-all handler for requests that don't match other tools.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("codexa.tools.enhanced.universal_fallback")
    
    @property
    def name(self) -> str:
        return "universal_fallback"
    
    @property
    def description(self) -> str:
        return "Universal fallback tool that can handle any request when no other tools match"
    
    @property
    def category(self) -> str:
        return "fallback"
    
    @property
    def priority(self) -> ToolPriority:
        return ToolPriority.LOW  # Always lowest priority
    
    @property
    def provides_capabilities(self) -> set:
        return {"fallback", "general_assistance", "request_handling"}
    
    @property
    def required_context(self) -> set:
        return set()  # No specific context required
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """
        Always return a low confidence for any non-empty request.
        
        This ensures that if no other tools match a request, this tool will
        be available as a fallback option.
        """
        if not request or not request.strip():
            return 0.0
        
        # Return a very low confidence that will only be used as last resort
        # This is lower than the 0.05 threshold used in tool selection
        return 0.01
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """
        Execute fallback handling for the request.
        
        This tool will attempt to:
        1. Use AI provider for general assistance
        2. Provide helpful guidance about available capabilities
        3. Suggest specific tools that might be more appropriate
        """
        try:
            request = getattr(context, 'user_request', '') or ''
            request = str(request).strip()
            
            self.logger.info(f"Universal fallback handling request: '{request}'")
            
            # Try to use AI provider for general assistance
            try:
                from ..ai_providers.ai_provider_tool import AIProviderTool
                ai_tool = AIProviderTool()
                
                # Create a more specific prompt for the AI
                enhanced_request = self._enhance_request_for_ai(request)
                
                # Create a new context with the enhanced request
                ai_context = ToolContext(
                    current_path=context.current_path,
                    user_request=enhanced_request,
                    session_id=context.session_id,
                    request_id=context.request_id
                )
                
                # Try to execute with AI provider
                ai_result = await ai_tool.execute(ai_context)
                if ai_result.success:
                    return ToolResult.success_result(
                        data=ai_result.data,
                        tool_name=self.name
                    )
                    
            except Exception as ai_error:
                self.logger.warning(f"AI provider fallback failed: {ai_error}")
            
            # If AI fails, provide general guidance
            guidance = self._generate_guidance(request)
            
            return ToolResult.success_result(
                data={
                    "request": request,
                    "guidance": guidance,
                    "suggested_actions": self._get_suggested_actions(request),
                    "available_capabilities": self._get_available_capabilities(),
                    "message": f"I'm not sure how to handle '{request}' specifically, but here's some guidance:"
                },
                tool_name=self.name
            )
            
        except Exception as e:
            self.logger.error(f"Universal fallback execution failed: {e}", exc_info=True)
            return ToolResult.error_result(
                error=f"Fallback handling failed: {str(e)}",
                tool_name=self.name
            )
    
    def _enhance_request_for_ai(self, request: str) -> str:
        """Enhance the request with context to help AI provide better assistance."""
        return f"""
I received a request that didn't match any specific tools: "{request}"

Please help me understand what the user might be trying to accomplish and provide helpful guidance. 
Consider that I have access to various tools for:
- File operations (create, read, write, delete files and directories)
- Code analysis and generation
- AI-powered assistance
- System operations
- Documentation and help

Please provide a helpful response that either:
1. Clarifies what the user might want to do
2. Suggests specific actions they could take
3. Offers to help with a related task

Be friendly and helpful in your response.
"""
    
    def _generate_guidance(self, request: str) -> str:
        """Generate helpful guidance for the request."""
        request_lower = request.lower()
        
        # Analyze the request for potential intent
        if any(word in request_lower for word in ['file', 'create', 'write', 'save']):
            return "It looks like you might want to work with files. I can help you create, read, write, or manage files and directories."
        
        elif any(word in request_lower for word in ['code', 'program', 'function', 'script']):
            return "It seems you might be interested in code-related tasks. I can help with code generation, analysis, and programming assistance."
        
        elif any(word in request_lower for word in ['help', 'what', 'how', 'can you']):
            return "I'm here to help! I can assist with various tasks including file operations, code generation, analysis, and general programming assistance."
        
        elif any(word in request_lower for word in ['delete', 'remove', 'clean']):
            return "If you want to delete or remove something, I can help with file and directory operations safely."
        
        else:
            return "I'm not sure exactly what you're looking for, but I'm here to help with various programming and file management tasks."
    
    def _get_suggested_actions(self, request: str) -> List[str]:
        """Get suggested actions based on the request."""
        request_lower = request.lower()
        suggestions = []
        
        # File-related suggestions
        if any(word in request_lower for word in ['file', 'create', 'write']):
            suggestions.extend([
                "Create a new file",
                "Write content to a file", 
                "List files in a directory",
                "Read an existing file"
            ])
        
        # Code-related suggestions
        if any(word in request_lower for word in ['code', 'program', 'function']):
            suggestions.extend([
                "Generate code for a specific task",
                "Analyze existing code",
                "Create a new script or function",
                "Review code for improvements"
            ])
        
        # General suggestions
        suggestions.extend([
            "Get help with available commands",
            "List available tools and capabilities",
            "Ask for assistance with a specific task"
        ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _get_available_capabilities(self) -> Dict[str, List[str]]:
        """Get available capabilities organized by category."""
        return {
            "File Operations": [
                "Create files and directories",
                "Read and write files", 
                "Delete files and directories",
                "Search files and content",
                "File validation and info"
            ],
            "Code Assistance": [
                "Generate code",
                "Analyze code",
                "Code validation and testing",
                "Multi-language support"
            ],
            "AI Features": [
                "Text generation",
                "Code analysis",
                "General AI assistance",
                "Provider switching"
            ],
            "System Tools": [
                "Directory operations",
                "File system navigation",
                "Performance monitoring",
                "Tool coordination"
            ]
        }