"""
Enhanced AI provider system for Codexa with runtime switching and intelligent routing.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .providers import AIProvider, OpenAIProvider, AnthropicProvider, OpenRouterProvider, OpenRouterOAIProvider
from .enhanced_config import EnhancedConfig, ModelConfig, ProviderConfig
from .config import Config


class ConfigAdapter:
    """Adapter to make EnhancedConfig compatible with legacy Config interface."""
    
    def __init__(self, enhanced_config: EnhancedConfig):
        self.enhanced_config = enhanced_config
    
    def get_provider(self) -> str:
        """Get the current provider."""
        return self.enhanced_config.get_provider()
    
    def get_model(self, provider: str = None) -> str:
        """Get the model for the specified provider."""
        return self.enhanced_config.get_model(provider)
    
    def get_api_key(self, provider: str = None) -> str:
        """Get the API key for the specified provider."""
        return self.enhanced_config.get_api_key(provider)
    
    def has_valid_config(self) -> bool:
        """Check if we have valid configuration."""
        return self.enhanced_config.has_valid_config()
    
    # Legacy property access for compatibility
    @property
    def openai_api_key(self) -> str:
        return self.enhanced_config.get_api_key("openai")
    
    @property
    def anthropic_api_key(self) -> str:
        return self.enhanced_config.get_api_key("anthropic")
    
    @property
    def openrouter_api_key(self) -> str:
        return self.enhanced_config.get_api_key("openrouter")
    
    @property
    def user_config(self) -> dict:
        return self.enhanced_config.user_config
    
    @property
    def openrouter_use_oai_client(self) -> bool:
        return self.enhanced_config.openrouter_use_oai_client


@dataclass
class ProviderMetrics:
    """Performance metrics for a provider."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    uptime_start: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return 1.0 - self.success_rate
    
    def update_request(self, success: bool, response_time: float):
        """Update metrics with new request data."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_response_time += response_time
        self.average_response_time = self.total_response_time / self.total_requests
        self.last_request_time = datetime.now()


class ProviderRouter:
    """Intelligent router for provider selection."""
    
    def __init__(self):
        self.routing_rules = []
        self.provider_scores: Dict[str, float] = {}
    
    def add_routing_rule(self, rule_func):
        """Add a routing rule function."""
        self.routing_rules.append(rule_func)
    
    def select_provider(self, providers: Dict[str, 'EnhancedAIProvider'],
                       request_context: Dict[str, Any]) -> Optional[str]:
        """Select best provider based on routing rules and performance."""
        available_providers = {
            name: provider for name, provider in providers.items()
            if provider.is_available() and provider.enabled
        }
        
        if not available_providers:
            return None
        
        # Apply routing rules
        for rule in self.routing_rules:
            result = rule(available_providers, request_context)
            if result:
                return result
        
        # Default: select by performance score
        best_provider = None
        best_score = -1
        
        for name, provider in available_providers.items():
            score = self._calculate_provider_score(provider)
            if score > best_score:
                best_score = score
                best_provider = name
        
        return best_provider
    
    def _calculate_provider_score(self, provider: 'EnhancedAIProvider') -> float:
        """Calculate provider score based on performance metrics."""
        metrics = provider.metrics
        
        # Base score from success rate
        score = metrics.success_rate * 100
        
        # Penalty for high response time (>2s)
        if metrics.average_response_time > 2.0:
            score -= (metrics.average_response_time - 2.0) * 10
        
        # Bonus for recent activity
        if metrics.last_request_time:
            hours_since_last = (datetime.now() - metrics.last_request_time).total_seconds() / 3600
            if hours_since_last < 1:
                score += 10
            elif hours_since_last > 24:
                score -= 5
        
        # Penalty for high error rate
        score -= metrics.error_rate * 50
        
        return max(0, score)


class EnhancedAIProvider(AIProvider):
    """Enhanced AI provider with metrics and advanced features."""
    
    def __init__(self, base_provider: AIProvider, config: ProviderConfig):
        self.base_provider = base_provider
        self.config = config
        self.metrics = ProviderMetrics()
        self.enabled = config.enabled
        self.logger = logging.getLogger(f"provider.{config.name}")
        
        # Initialize uptime tracking
        if self.is_available():
            self.metrics.uptime_start = datetime.now()
    
    def ask(self, prompt: str, history: Optional[List[Dict]] = None,
             context: Optional[str] = None, model: Optional[str] = None) -> str:
        """Enhanced ask method with metrics tracking."""
        start_time = datetime.now()

        try:
            # Use specific model if provided
            if model and hasattr(self.base_provider, 'model'):
                original_model = self.base_provider.model
                self.base_provider.model = model

            # Call base provider (synchronous call)
            response = self.base_provider.ask(prompt, history, context)

            # Restore original model
            if model and hasattr(self.base_provider, 'model'):
                self.base_provider.model = original_model

            # Update metrics
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics.update_request(True, response_time)

            self.logger.debug(f"Request completed in {response_time:.2f}s")
            return response

        except Exception as e:
            # Update metrics for failure
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics.update_request(False, response_time)

            self.logger.error(f"Request failed after {response_time:.2f}s: {e}")
            raise

    async def ask_async(self, prompt: str, history: Optional[List[Dict]] = None,
                       context: Optional[str] = None, model: Optional[str] = None) -> str:
        """Async version of ask method for compatibility with async interfaces."""
        # Since the base provider's ask method is synchronous, we run it in a thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.ask, prompt, history, context, model)
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.base_provider.is_available()
    
    def get_models(self) -> List[str]:
        """Get available models for this provider."""
        return [model.name for model in self.config.models if model.enabled]

    def get_available_models(self) -> List[Dict[str, str]]:
        """Get available models from the provider's API (implements abstract method)."""
        if hasattr(self.base_provider, 'get_available_models'):
            return self.base_provider.get_available_models()
        return []

    def get_available_models_from_api(self) -> List[Dict[str, str]]:
        """Get available models from the provider's API."""
        if hasattr(self.base_provider, 'get_available_models'):
            return self.base_provider.get_available_models()
        return []
    
    def get_capabilities(self, model: Optional[str] = None) -> List[str]:
        """Get capabilities for provider or specific model."""
        if model:
            for model_config in self.config.models:
                if model_config.name == model:
                    return model_config.capabilities
        
        # Return all capabilities from all models
        capabilities = set()
        for model_config in self.config.models:
            capabilities.update(model_config.capabilities)
        return list(capabilities)
    
    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """Get the system prompt for the enhanced provider."""
        # Delegate to base provider if it has the method
        if hasattr(self.base_provider, '_get_system_prompt'):
            return self.base_provider._get_system_prompt(context)
        
        # Fallback to centralized system prompt
        from .system_prompt import get_codexa_system_prompt
        return get_codexa_system_prompt(context)
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status information."""
        uptime = None
        if self.metrics.uptime_start:
            uptime = str(datetime.now() - self.metrics.uptime_start)
        
        return {
            "name": self.config.name,
            "enabled": self.enabled,
            "available": self.is_available(),
            "priority": self.config.priority,
            "models": len(self.config.models),
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.success_rate,
                "average_response_time": self.metrics.average_response_time,
                "last_request": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None,
                "uptime": uptime
            }
        }


class EnhancedProviderFactory:
    """Factory for creating enhanced providers."""
    
    def __init__(self, config: EnhancedConfig):
        self.config = config
        self.providers: Dict[str, EnhancedAIProvider] = {}
        self.router = ProviderRouter()
        self.logger = logging.getLogger("provider.factory")
        
        self._initialize_providers()
        self._setup_routing_rules()
    
    def _initialize_providers(self):
        """Initialize all configured providers."""
        for name, provider_config in self.config.providers.items():
            try:
                # Create base provider
                base_provider = self._create_base_provider(name, provider_config)
                if not base_provider:
                    continue
                
                # Wrap with enhanced provider
                enhanced_provider = EnhancedAIProvider(base_provider, provider_config)
                self.providers[name] = enhanced_provider
                
                self.logger.info(f"Initialized provider: {name}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize provider {name}: {e}")
    
    def _create_base_provider(self, name: str, config: ProviderConfig) -> Optional[AIProvider]:
        """Create base provider instance."""
        # Create adapter for legacy compatibility
        config_adapter = ConfigAdapter(self.config)
        
        if name == "openai":
            return OpenAIProvider(config_adapter)
        elif name == "anthropic":
            return AnthropicProvider(config_adapter)
        elif name == "openrouter":
            # Use the OAI client approach by default for enhanced providers
            use_oai_client = getattr(config, 'use_oai_client', True)
            if use_oai_client:
                return OpenRouterOAIProvider(config_adapter)
            else:
                return OpenRouterProvider(config_adapter)
        elif name == "openrouter-http":
            # Explicit HTTP requests approach
            return OpenRouterProvider(config_adapter)
        elif name == "openrouter-oai":
            # Explicit OpenAI client approach
            return OpenRouterOAIProvider(config_adapter)
        else:
            self.logger.warning(f"Unknown provider type: {name}")
            return None
    
    def _setup_routing_rules(self):
        """Setup intelligent routing rules."""
        
        # Rule 1: Code analysis tasks prefer high-capability models
        def code_analysis_rule(providers, context):
            if context.get('task_type') == 'code_analysis':
                for name, provider in providers.items():
                    if 'reasoning' in provider.get_capabilities():
                        return name
            return None
        
        # Rule 2: Simple tasks prefer fast/cheap models
        def simple_task_rule(providers, context):
            if context.get('complexity', 'medium') == 'low':
                # Prefer providers with better response times
                best_provider = None
                best_time = float('inf')
                
                for name, provider in providers.items():
                    avg_time = provider.metrics.average_response_time
                    if avg_time > 0 and avg_time < best_time:
                        best_time = avg_time
                        best_provider = name
                
                return best_provider
            return None
        
        # Rule 3: Fallback to highest priority available provider
        def priority_fallback_rule(providers, context):
            if providers:
                return max(providers.keys(), 
                          key=lambda name: providers[name].config.priority)
            return None
        
        self.router.add_routing_rule(code_analysis_rule)
        self.router.add_routing_rule(simple_task_rule)
        self.router.add_routing_rule(priority_fallback_rule)
    
    def get_provider(self, name: Optional[str] = None, 
                    context: Optional[Dict[str, Any]] = None) -> Optional[EnhancedAIProvider]:
        """Get provider by name or intelligent selection."""
        context = context or {}
        
        if name:
            # Specific provider requested
            provider = self.providers.get(name)
            if provider and provider.is_available() and provider.enabled:
                return provider
            else:
                self.logger.warning(f"Requested provider '{name}' not available")
                return None
        
        # Intelligent provider selection
        selected_name = self.router.select_provider(self.providers, context)
        return self.providers.get(selected_name) if selected_name else None
    
    def switch_provider(self, provider_name: str) -> bool:
        """Switch to a specific provider."""
        if provider_name not in self.providers:
            self.logger.error(f"Provider '{provider_name}' not found")
            return False
        
        provider = self.providers[provider_name]
        if not provider.is_available():
            self.logger.error(f"Provider '{provider_name}' not available")
            return False
        
        # Update configuration
        self.config.switch_provider(provider_name)
        self.logger.info(f"Switched to provider: {provider_name}")
        return True
    
    def switch_model(self, model_name: str, provider_name: Optional[str] = None) -> bool:
        """Switch to a specific model."""
        provider_name = provider_name or self.config.get_provider()
        
        if provider_name not in self.providers:
            return False
        
        provider = self.providers[provider_name]
        available_models = provider.get_models()
        
        if model_name not in available_models:
            self.logger.error(f"Model '{model_name}' not available in provider '{provider_name}'")
            return False
        
        # Update configuration
        success = self.config.switch_model(model_name, provider_name)
        if success:
            self.logger.info(f"Switched to model: {model_name} ({provider_name})")
        
        return success
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [
            name for name, provider in self.providers.items()
            if provider.is_available() and provider.enabled
        ]
    
    def get_available_models(self, provider_name: Optional[str] = None) -> Dict[str, List[str]]:
        """Get available models by provider."""
        if provider_name:
            provider = self.providers.get(provider_name)
            if provider:
                return {provider_name: provider.get_models()}
            return {}
        
        # Return all available models
        result = {}
        for name, provider in self.providers.items():
            if provider.is_available() and provider.enabled:
                result[name] = provider.get_models()
        
        return result

    def get_available_models_from_api(self, provider_name: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
        """Get available models from provider APIs."""
        if provider_name:
            provider = self.providers.get(provider_name)
            if provider and provider.is_available() and provider.enabled:
                return {provider_name: provider.get_available_models_from_api()}
            return {}
        
        # Return all available models from all provider APIs
        result = {}
        for name, provider in self.providers.items():
            if provider.is_available() and provider.enabled:
                models = provider.get_available_models_from_api()
                if models:  # Only include providers that return models
                    result[name] = models
        
        return result
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all providers."""
        return {name: provider.get_status() for name, provider in self.providers.items()}
    
    def enable_provider(self, provider_name: str) -> bool:
        """Enable a provider."""
        if provider_name in self.providers:
            self.providers[provider_name].enabled = True
            self.logger.info(f"Enabled provider: {provider_name}")
            return True
        return False
    
    def disable_provider(self, provider_name: str) -> bool:
        """Disable a provider."""
        if provider_name in self.providers:
            self.providers[provider_name].enabled = False
            self.logger.info(f"Disabled provider: {provider_name}")
            return True
        return False
    
    def get_recommendation(self, task_description: str) -> Dict[str, Any]:
        """Get provider/model recommendation for a task."""
        context = self._analyze_task(task_description)
        recommended_provider_name = self.router.select_provider(self.providers, context)
        
        if not recommended_provider_name:
            return {"error": "No suitable provider available"}
        
        provider = self.providers[recommended_provider_name]
        recommended_models = []
        
        # Find suitable models based on task context
        for model_config in provider.config.models:
            if any(cap in model_config.capabilities for cap in context.get('required_capabilities', [])):
                recommended_models.append(model_config.name)
        
        return {
            "provider": recommended_provider_name,
            "models": recommended_models or provider.get_models()[:3],
            "reasoning": context.get('reasoning', 'Based on availability and performance'),
            "confidence": context.get('confidence', 0.8)
        }
    
    def _analyze_task(self, task_description: str) -> Dict[str, Any]:
        """Analyze task description to determine requirements."""
        task_lower = task_description.lower()
        
        # Determine task type
        task_type = "general"
        required_capabilities = []
        complexity = "medium"
        
        if any(keyword in task_lower for keyword in ["analyze", "debug", "explain", "review"]):
            task_type = "code_analysis"
            required_capabilities = ["analysis", "reasoning"]
            complexity = "high"
        elif any(keyword in task_lower for keyword in ["generate", "create", "build", "write"]):
            task_type = "generation"
            required_capabilities = ["code", "generation"]
        elif any(keyword in task_lower for keyword in ["simple", "quick", "basic"]):
            complexity = "low"
        
        return {
            "task_type": task_type,
            "required_capabilities": required_capabilities,
            "complexity": complexity,
            "reasoning": f"Detected {task_type} task with {complexity} complexity"
        }