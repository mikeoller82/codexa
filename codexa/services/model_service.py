"""
Model discovery and selection service for Codexa.
"""

import asyncio
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging

from ..ui.provider_selector import ModelInfo, ProviderInfo
from ..providers import ProviderFactory
from ..enhanced_providers import EnhancedProviderFactory
from ..config import Config
from ..enhanced_config import EnhancedConfig


logger = logging.getLogger(__name__)


@dataclass
class ModelDiscoveryResult:
    """Result of model discovery from provider APIs."""
    provider: str
    models: List[Dict[str, str]]
    success: bool
    error: Optional[str] = None
    response_time: float = 0.0


class ModelService:
    """Service for discovering and managing available models."""
    
    def __init__(self, config):
        self.config = config
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_discovery = {}
        
        # Determine if using enhanced config
        self.is_enhanced = isinstance(config, EnhancedConfig)
        
    def discover_all_models(self, timeout: float = 30.0) -> Dict[str, ModelDiscoveryResult]:
        """Discover available models from all providers concurrently."""
        providers = self._get_available_providers()
        
        if not providers:
            logger.warning("No providers available for model discovery")
            return {}
        
        # Use ThreadPoolExecutor for concurrent API calls
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            # Submit discovery tasks
            future_to_provider = {
                executor.submit(self._discover_provider_models, provider): provider
                for provider in providers
            }
            
            # Collect results with timeout
            for future in as_completed(future_to_provider, timeout=timeout):
                provider = future_to_provider[future]
                try:
                    result = future.result()
                    results[provider] = result
                except Exception as e:
                    logger.error(f"Error discovering models for {provider}: {e}")
                    results[provider] = ModelDiscoveryResult(
                        provider=provider,
                        models=[],
                        success=False,
                        error=str(e)
                    )
        
        return results
    
    def _discover_provider_models(self, provider_name: str) -> ModelDiscoveryResult:
        """Discover models for a single provider."""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{provider_name}_models"
        if self._is_cache_valid(cache_key):
            cached_result = self.cache[cache_key]
            logger.debug(f"Using cached models for {provider_name}")
            return cached_result
        
        try:
            # Try enhanced provider first, fallback to basic
            provider = self._get_provider_instance(provider_name)
            if not provider:
                return ModelDiscoveryResult(
                    provider=provider_name,
                    models=[],
                    success=False,
                    error="Provider not available"
                )
            
            # Get models from API
            if hasattr(provider, 'get_available_models'):
                models = provider.get_available_models()
            else:
                models = []
            
            response_time = time.time() - start_time
            
            result = ModelDiscoveryResult(
                provider=provider_name,
                models=models,
                success=True,
                response_time=response_time
            )
            
            # Cache the result
            self.cache[cache_key] = result
            self.last_discovery[cache_key] = time.time()
            
            logger.info(f"Discovered {len(models)} models for {provider_name} in {response_time:.2f}s")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Failed to discover models for {provider_name}: {e}")
            
            return ModelDiscoveryResult(
                provider=provider_name,
                models=[],
                success=False,
                error=str(e),
                response_time=response_time
            )
    
    def get_models_for_provider(self, provider_name: str, 
                               force_refresh: bool = False) -> List[Dict[str, str]]:
        """Get models for a specific provider."""
        cache_key = f"{provider_name}_models"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            return self.cache[cache_key].models
        
        result = self._discover_provider_models(provider_name)
        return result.models if result.success else []
    
    def convert_to_model_info(self, models_data: Dict[str, ModelDiscoveryResult]) -> List[ModelInfo]:
        """Convert discovery results to ModelInfo objects."""
        model_infos = []
        
        for provider_name, result in models_data.items():
            if not result.success:
                continue
                
            for model_data in result.models:
                # Determine cost tier based on model name/provider
                cost_tier = self._determine_cost_tier(model_data, provider_name)
                
                # Extract capabilities from model data
                capabilities = self._extract_capabilities(model_data, provider_name)
                
                model_info = ModelInfo(
                    name=model_data.get('id', model_data.get('name', '')),
                    display_name=model_data.get('name', model_data.get('id', '')),
                    provider=provider_name,
                    capabilities=capabilities,
                    context_length=model_data.get('context_length', 0),
                    cost_tier=cost_tier
                )
                
                model_infos.append(model_info)
        
        # Sort by provider, then by model name
        model_infos.sort(key=lambda x: (x.provider, x.name))
        return model_infos
    
    def get_provider_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics about provider model discovery."""
        stats = {}
        
        for provider in self._get_available_providers():
            cache_key = f"{provider}_models"
            
            if cache_key in self.cache:
                result = self.cache[cache_key]
                stats[provider] = {
                    "model_count": len(result.models),
                    "last_discovery": self.last_discovery.get(cache_key, 0),
                    "response_time": result.response_time,
                    "success": result.success,
                    "error": result.error
                }
            else:
                stats[provider] = {
                    "model_count": 0,
                    "last_discovery": 0,
                    "response_time": 0,
                    "success": False,
                    "error": "Not discovered yet"
                }
        
        return stats
    
    def clear_cache(self, provider_name: Optional[str] = None):
        """Clear model cache."""
        if provider_name:
            cache_key = f"{provider_name}_models"
            self.cache.pop(cache_key, None)
            self.last_discovery.pop(cache_key, None)
        else:
            self.cache.clear()
            self.last_discovery.clear()
        
        logger.info(f"Cleared model cache for {provider_name or 'all providers'}")
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        providers = []
        
        if self.is_enhanced:
            # Use enhanced config
            providers = self.config.get_available_providers()
            logger.debug(f"Using enhanced config, found providers: {providers}")
        else:
            # Check basic providers
            try:
                factory = ProviderFactory()
                if self.config.get_api_key("openai"):
                    providers.append("openai")
                if self.config.get_api_key("anthropic"):
                    providers.append("anthropic")
                if self.config.get_api_key("openrouter"):
                    providers.append("openrouter")
            except Exception as e:
                logger.debug(f"Error checking basic providers: {e}")
        
        return providers
    
    def _get_provider_instance(self, provider_name: str):
        """Get provider instance."""
        try:
            if self.is_enhanced:
                # Use enhanced provider factory
                factory = EnhancedProviderFactory(self.config)
                provider = factory.get_provider(provider_name)
                return provider
            else:
                # Use basic provider factory
                factory = ProviderFactory()
                # Temporarily set the provider to get instance
                original_provider = self.config.get_provider()
                
                # Create config with specific provider
                temp_config = Config()
                temp_config.default_provider = provider_name
                
                provider = factory.create_provider(temp_config)
                return provider
            
        except Exception as e:
            logger.error(f"Error creating provider instance for {provider_name}: {e}")
            return None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid."""
        if cache_key not in self.cache:
            return False
        
        last_update = self.last_discovery.get(cache_key, 0)
        return time.time() - last_update < self.cache_ttl
    
    def _determine_cost_tier(self, model_data: Dict[str, str], provider: str) -> str:
        """Determine cost tier based on model and provider."""
        model_name = model_data.get('name', '').lower()
        model_id = model_data.get('id', '').lower()
        
        # Check pricing data if available
        pricing = model_data.get('pricing', {})
        if pricing:
            prompt_cost = pricing.get('prompt', 0)
            if isinstance(prompt_cost, str):
                try:
                    prompt_cost = float(prompt_cost)
                except ValueError:
                    prompt_cost = 0
            
            if prompt_cost == 0:
                return "free"
            elif prompt_cost < 0.001:
                return "low"
            elif prompt_cost < 0.01:
                return "medium"
            else:
                return "high"
        
        # Fallback to heuristics
        if provider == "openrouter":
            if "free" in model_id or "free" in model_name:
                return "free"
            elif any(x in model_id for x in ["gpt-4", "claude-3", "opus"]):
                return "high"
            elif any(x in model_id for x in ["gpt-3.5", "haiku", "sonnet"]):
                return "medium"
            else:
                return "low"
        
        elif provider == "openai":
            if "gpt-4" in model_name:
                return "high"
            elif "gpt-3.5" in model_name:
                return "medium"
            else:
                return "low"
        
        elif provider == "anthropic":
            if "opus" in model_name:
                return "high"
            elif "sonnet" in model_name:
                return "medium"
            elif "haiku" in model_name:
                return "low"
        
        return "unknown"
    
    def _extract_capabilities(self, model_data: Dict[str, str], provider: str) -> List[str]:
        """Extract capabilities from model data."""
        capabilities = []
        
        model_name = model_data.get('name', '').lower()
        model_id = model_data.get('id', '').lower()
        
        # Basic capabilities
        capabilities.append("text-generation")
        
        # Code capabilities
        if any(x in model_name or x in model_id for x in ["code", "coding", "program"]):
            capabilities.append("code")
        
        # Analysis capabilities
        if any(x in model_name or x in model_id for x in ["gpt-4", "claude-3", "opus", "sonnet"]):
            capabilities.extend(["analysis", "reasoning"])
        
        # Fast/efficient models
        if any(x in model_name or x in model_id for x in ["turbo", "fast", "haiku", "3.5"]):
            capabilities.append("fast")
        
        # Large context
        context_length = model_data.get('context_length', 0)
        if context_length > 100000:
            capabilities.append("large-context")
        
        return capabilities


class InteractiveModelSelector:
    """Interactive model selection interface."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        from ..ui.provider_selector import ModelSelector
        self.selector = ModelSelector()
    
    async def select_model_interactive(self, provider_name: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Interactively select a model with real-time API discovery."""
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        console = Console()
        
        # Show discovery progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            discovery_task = progress.add_task("Discovering available models...", total=None)
            
            # Run discovery
            if provider_name:
                models_data = {
                    provider_name: self.model_service._discover_provider_models(provider_name)
                }
            else:
                models_data = self.model_service.discover_all_models()
            
            progress.remove_task(discovery_task)
        
        # Convert to ModelInfo objects
        model_infos = self.model_service.convert_to_model_info(models_data)
        
        if not model_infos:
            console.print("[red]No models available from any provider[/red]")
            return None
        
        # Show summary
        provider_counts = {}
        for model in model_infos:
            provider_counts[model.provider] = provider_counts.get(model.provider, 0) + 1
        
        summary_lines = [f"{provider}: {count} models" for provider, count in provider_counts.items()]
        summary_panel = Panel(
            "\n".join(summary_lines),
            title=f"Discovered {len(model_infos)} models",
            border_style="green"
        )
        console.print(summary_panel)
        
        # Filter by provider if specified
        if provider_name:
            model_infos = [m for m in model_infos if m.provider == provider_name]
        
        # Interactive selection
        selected_model = self.selector.select_model(model_infos)
        
        if selected_model:
            return (selected_model.provider, selected_model.name)
        
        return None