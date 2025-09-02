"""
Generic AI Provider Tool for Codexa.
Provides a unified interface to different AI providers and handles provider selection.
"""

import asyncio
from typing import Dict, List, Set, Optional, Any
import logging

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority


class AIProviderTool(Tool):
    """
    Generic AI provider interface tool.
    
    This tool handles:
    - Provider selection and management
    - Generic AI requests
    - Provider fallback and error handling
    - Provider health monitoring
    """
    
    @property
    def name(self) -> str:
        return "ai_provider"
    
    @property
    def description(self) -> str:
        return "Generic AI provider interface for unified AI operations"
    
    @property
    def category(self) -> str:
        return "ai"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "ai_provider", "provider_management", "ai_generic", 
            "provider_selection", "ai_fallback"
        }
    
    @property
    def priority(self) -> ToolPriority:
        return ToolPriority.NORMAL
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("codexa.tools.ai.provider")
        self._provider_health_cache = {}
        self._last_successful_provider = None
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        confidence = 0.0
        
        # High confidence for explicit AI/model requests
        if any(phrase in request_lower for phrase in [
            "/model select", "model select", "select model", "switch model",
            "ai provider", "provider", "change provider", "switch provider"
        ]):
            return 0.9
            
        # Medium confidence for general AI requests
        ai_keywords = ["ai", "gpt", "claude", "llm", "model", "generate", "ask ai"]
        for keyword in ai_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.6)
        
        # Higher confidence as fallback for general requests when no other tools match
        if any(word in request_lower for word in ["create", "generate", "explain", "analyze", "help", "fix"]):
            confidence = max(confidence, 0.4)
        
        # Even lower confidence for any request that contains common words
        # This ensures AI provider is available as a last resort
        common_words = ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]
        if any(word in request_lower for word in common_words):
            confidence = max(confidence, 0.1)
        
        # Absolute fallback - any non-empty request gets minimal confidence
        if request_lower.strip():
            confidence = max(confidence, 0.05)
        
        return confidence
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute AI request using available providers."""
        try:
            if not context.user_request:
                return ToolResult.error_result(
                    error="No request provided for AI provider",
                    tool_name=self.name
                )
            
            # Get available providers
            providers = self._get_available_providers(context)
            
            if not providers:
                return ToolResult.error_result(
                    error="No AI providers available",
                    tool_name=self.name
                )
            
            # Select best provider for this request
            selected_provider = await self._select_provider(providers, context)
            
            if not selected_provider:
                return ToolResult.error_result(
                    error="No suitable AI provider found",
                    tool_name=self.name
                )
            
            # Create optimized prompt
            prompt = self._create_generic_prompt(context.user_request, context)
            
            # Execute with selected provider
            try:
                result = await self._execute_with_provider(selected_provider, prompt)
                
                if not result:
                    # Try fallback providers
                    for fallback_provider in providers:
                        if fallback_provider != selected_provider:
                            try:
                                result = await self._execute_with_provider(fallback_provider, prompt)
                                if result:
                                    selected_provider = fallback_provider
                                    break
                            except Exception as e:
                                self.logger.debug(f"Fallback provider failed: {e}")
                                continue
                
                if not result:
                    return ToolResult.error_result(
                        error="All AI providers failed to generate response",
                        tool_name=self.name
                    )
                
                # Update provider success tracking
                self._last_successful_provider = selected_provider
                self._update_provider_health(selected_provider, True)
                
                # Format result
                result_data = {
                    "response": result,
                    "provider_used": selected_provider.__class__.__name__ if hasattr(selected_provider, '__class__') else "Unknown",
                    "prompt_length": len(prompt),
                    "fallback_used": selected_provider != providers[0] if providers else False
                }
                
                return ToolResult.success_result(
                    data=result_data,
                    tool_name=self.name,
                    output=result
                )
                
            except Exception as provider_error:
                self._update_provider_health(selected_provider, False)
                return ToolResult.error_result(
                    error=f"AI provider execution error: {str(provider_error)}",
                    tool_name=self.name
                )
                
        except Exception as e:
            self.logger.error(f"AI provider tool execution failed: {e}")
            return ToolResult.error_result(
                error=f"AI provider tool error: {str(e)}",
                tool_name=self.name
            )
    
    def _get_available_providers(self, context: ToolContext) -> List[Any]:
        """Get list of available AI providers from context."""
        providers = []
        
        # Primary provider from context
        if context.provider:
            providers.append(context.provider)
        
        # Additional providers from config or context
        if hasattr(context, 'config') and context.config:
            # Try to get additional providers from config
            try:
                if hasattr(context.config, 'get_ai_providers'):
                    additional_providers = context.config.get_ai_providers()
                    providers.extend(additional_providers)
            except Exception as e:
                self.logger.debug(f"Could not get additional providers: {e}")
        
        return providers
    
    async def _select_provider(self, providers: List[Any], context: ToolContext) -> Optional[Any]:
        """Select the best provider for this request."""
        if not providers:
            return None
        
        # If we have a last successful provider, prefer it
        if self._last_successful_provider in providers:
            health = self._provider_health_cache.get(self._last_successful_provider, {})
            if health.get("success_rate", 0) > 0.5:
                return self._last_successful_provider
        
        # Otherwise, select based on health and capabilities
        best_provider = None
        best_score = -1
        
        for provider in providers:
            score = await self._score_provider(provider, context)
            if score > best_score:
                best_score = score
                best_provider = provider
        
        return best_provider if best_score > 0 else providers[0]  # Fallback to first
    
    async def _score_provider(self, provider: Any, context: ToolContext) -> float:
        """Score a provider based on health, capabilities, and suitability."""
        score = 0.5  # Base score
        
        # Health score
        health = self._provider_health_cache.get(provider, {})
        success_rate = health.get("success_rate", 0.5)
        score += success_rate * 0.3
        
        # Availability score
        try:
            if hasattr(provider, 'is_available') and callable(provider.is_available):
                if provider.is_available():
                    score += 0.2
            else:
                score += 0.1  # Assume available if can't check
        except Exception:
            pass
        
        # Capability match (basic heuristics)
        request = context.user_request.lower()
        if hasattr(provider, 'capabilities'):
            capabilities = provider.capabilities
            if isinstance(capabilities, (list, set)):
                if "code" in request and "code_generation" in capabilities:
                    score += 0.2
                if "analyze" in request and "analysis" in capabilities:
                    score += 0.2
        
        return min(score, 1.0)
    
    def _create_generic_prompt(self, request: str, context: ToolContext) -> str:
        """Create a generic prompt optimized for AI providers."""
        prompt_parts = []
        
        # Add context if available
        if context.project_info and context.project_info.get("name"):
            prompt_parts.append(f"Project context: {context.project_info['name']}")
        
        # Add clear instruction
        prompt_parts.append("Please provide a helpful and accurate response to the following request:")
        
        # Add the actual request
        prompt_parts.append(request)
        
        return "\n\n".join(prompt_parts)
    
    async def _execute_with_provider(self, provider: Any, prompt: str) -> str:
        """Execute request with a specific provider."""
        # Try common provider methods
        methods_to_try = [
            'generate', 'generate_text', 'complete', 'chat', 
            'ask', 'query', 'respond', '__call__'
        ]
        
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
                        self.logger.debug(f"Provider method {method_name} failed: {e}")
                        continue
        
        raise Exception(f"Provider {provider} has no compatible methods")
    
    def _update_provider_health(self, provider: Any, success: bool) -> None:
        """Update provider health tracking."""
        if provider not in self._provider_health_cache:
            self._provider_health_cache[provider] = {
                "total_calls": 0,
                "successful_calls": 0,
                "success_rate": 0.0
            }
        
        health = self._provider_health_cache[provider]
        health["total_calls"] += 1
        
        if success:
            health["successful_calls"] += 1
        
        health["success_rate"] = health["successful_calls"] / health["total_calls"]
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider health and usage statistics."""
        return {
            "tracked_providers": len(self._provider_health_cache),
            "last_successful_provider": str(self._last_successful_provider) if self._last_successful_provider else None,
            "provider_health": {
                str(provider): health 
                for provider, health in self._provider_health_cache.items()
            }
        }