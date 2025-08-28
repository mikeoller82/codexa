"""
AI Text Generation Tool for Codexa.
Handles text generation, completion, and writing tasks using AI providers.
"""

import asyncio
from typing import Dict, List, Set, Optional, Any
import logging

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority


class AITextGenerationTool(Tool):
    """
    Tool for AI-powered text generation and completion.
    
    This tool handles:
    - Text generation and completion
    - Documentation writing
    - Content creation
    - Text summarization
    - Language translation
    """
    
    @property
    def name(self) -> str:
        return "ai_text_generation"
    
    @property
    def description(self) -> str:
        return "AI-powered text generation, completion, and writing tasks"
    
    @property
    def category(self) -> str:
        return "ai"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "text_generation", "content_creation", "documentation_writing",
            "text_completion", "summarization", "translation", "ai_text_generation"
        }
    
    @property
    def priority(self) -> ToolPriority:
        return ToolPriority.HIGH
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("codexa.tools.ai.text_generation")
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        confidence = 0.0
        
        # High confidence for explicit text generation requests
        text_generation_keywords = [
            "write text", "generate text", "create content", "write documentation",
            "compose", "draft", "summarize", "translate", "explain", "describe"
        ]
        
        for keyword in text_generation_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.9)
        
        # Medium confidence for general AI text tasks
        general_text_keywords = ["write", "generate", "create", "explain", "summarize"]
        for keyword in general_text_keywords:
            if keyword in request_lower and "code" not in request_lower:
                confidence = max(confidence, 0.7)
        
        # Boost for documentation requests
        if any(word in request_lower for word in ["documentation", "readme", "guide", "tutorial"]):
            confidence = max(confidence, 0.8)
        
        return confidence
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute text generation using AI provider."""
        try:
            if not context.user_request:
                return ToolResult.error_result(
                    error="No request provided for text generation",
                    tool_name=self.name
                )
            
            # Check if AI provider is available
            provider = context.provider
            if not provider:
                return ToolResult.error_result(
                    error="No AI provider available for text generation",
                    tool_name=self.name
                )
            
            # Parse the request to determine what kind of text to generate
            request_analysis = self._analyze_text_request(context.user_request)
            
            # Generate prompt for AI provider
            prompt = self._create_text_generation_prompt(
                context.user_request,
                request_analysis,
                context
            )
            
            # Generate text using AI provider
            try:
                # Use provider's generate method if available
                if hasattr(provider, 'generate_text'):
                    generated_text = await provider.generate_text(prompt)
                elif hasattr(provider, 'generate'):
                    generated_text = await provider.generate(prompt)
                elif hasattr(provider, 'complete'):
                    generated_text = await provider.complete(prompt)
                else:
                    # Fallback for generic provider
                    generated_text = await self._generic_provider_call(provider, prompt)
                
                if not generated_text:
                    return ToolResult.error_result(
                        error="AI provider returned empty response",
                        tool_name=self.name
                    )
                
                # Format the result
                result_data = {
                    "generated_text": generated_text,
                    "request_type": request_analysis["type"],
                    "provider_used": provider.__class__.__name__ if hasattr(provider, '__class__') else "Unknown",
                    "prompt_length": len(prompt)
                }
                
                return ToolResult.success_result(
                    data=result_data,
                    tool_name=self.name,
                    output=generated_text
                )
                
            except Exception as provider_error:
                return ToolResult.error_result(
                    error=f"AI provider error: {str(provider_error)}",
                    tool_name=self.name
                )
                
        except Exception as e:
            self.logger.error(f"Text generation failed: {e}")
            return ToolResult.error_result(
                error=f"Text generation error: {str(e)}",
                tool_name=self.name
            )
    
    def _analyze_text_request(self, request: str) -> Dict[str, Any]:
        """Analyze the text generation request to determine type and parameters."""
        request_lower = request.lower()
        
        analysis = {
            "type": "general",
            "length": "medium",
            "style": "professional",
            "format": "plain_text"
        }
        
        # Determine text type
        if any(word in request_lower for word in ["documentation", "readme", "guide"]):
            analysis["type"] = "documentation"
            analysis["format"] = "markdown"
        elif any(word in request_lower for word in ["email", "letter", "message"]):
            analysis["type"] = "communication"
        elif any(word in request_lower for word in ["summary", "summarize"]):
            analysis["type"] = "summary"
        elif any(word in request_lower for word in ["translate", "translation"]):
            analysis["type"] = "translation"
        elif any(word in request_lower for word in ["explain", "describe"]):
            analysis["type"] = "explanation"
        
        # Determine length
        if any(word in request_lower for word in ["brief", "short", "concise"]):
            analysis["length"] = "short"
        elif any(word in request_lower for word in ["detailed", "comprehensive", "long"]):
            analysis["length"] = "long"
        
        # Determine style
        if any(word in request_lower for word in ["formal", "professional"]):
            analysis["style"] = "formal"
        elif any(word in request_lower for word in ["casual", "informal", "friendly"]):
            analysis["style"] = "casual"
        elif any(word in request_lower for word in ["technical", "precise"]):
            analysis["style"] = "technical"
        
        return analysis
    
    def _create_text_generation_prompt(self, request: str, analysis: Dict[str, Any], context: ToolContext) -> str:
        """Create an optimized prompt for AI text generation."""
        
        # Base prompt with context
        prompt_parts = []
        
        # Add context if available
        if context.project_info and context.project_info.get("name"):
            prompt_parts.append(f"Project: {context.project_info['name']}")
        
        # Add specific instructions based on analysis
        if analysis["type"] == "documentation":
            prompt_parts.append("Create clear, well-structured documentation with appropriate headings and examples.")
        elif analysis["type"] == "summary":
            prompt_parts.append("Provide a concise summary highlighting key points.")
        elif analysis["type"] == "explanation":
            prompt_parts.append("Provide a clear, detailed explanation that is easy to understand.")
        
        # Add style instructions
        style_instructions = {
            "formal": "Use formal, professional language.",
            "casual": "Use casual, friendly language.",
            "technical": "Use precise, technical language with appropriate terminology."
        }
        prompt_parts.append(style_instructions.get(analysis["style"], "Use clear, professional language."))
        
        # Add length guidance
        length_instructions = {
            "short": "Keep the response concise and to the point.",
            "medium": "Provide a well-balanced response with adequate detail.",
            "long": "Provide a comprehensive, detailed response."
        }
        prompt_parts.append(length_instructions.get(analysis["length"], ""))
        
        # Add the actual request
        prompt_parts.append(f"Request: {request}")
        
        return "\n\n".join(filter(None, prompt_parts))
    
    async def _generic_provider_call(self, provider: Any, prompt: str) -> str:
        """Generic fallback for calling AI providers."""
        # Try common method names
        methods_to_try = ['chat', 'ask', 'query', '__call__']
        
        for method_name in methods_to_try:
            if hasattr(provider, method_name):
                method = getattr(provider, method_name)
                if callable(method):
                    try:
                        if asyncio.iscoroutinefunction(method):
                            result = await method(prompt)
                        else:
                            result = method(prompt)
                        
                        if result:
                            return str(result)
                    except Exception as e:
                        self.logger.debug(f"Failed to call {method_name}: {e}")
                        continue
        
        raise Exception("Unable to call AI provider - no compatible methods found")