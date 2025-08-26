"""Configuration management for Codexa."""

import os
from pathlib import Path
from typing import Dict, Optional, List
import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager for Codexa."""

    def __init__(self):
        """Initialize configuration with environment variables and config files."""
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Default configuration
        self.default_provider = "openrouter"
        self.default_models = {
            "openai": "gpt-5",
            "anthropic": "claude-4-sonnet",
            "openrouter": "moonshotai/kimi-k2:free"
        }
        
        # Load user config if it exists
        self.user_config = self._load_user_config()
        
        # OpenRouter preferences  
        openrouter_config = self.user_config.get("openrouter", {})
        self.openrouter_use_oai_client = openrouter_config.get("use_oai_client", True)
    
    def _load_user_config(self) -> Dict:
        """Load user configuration from ~/.codexarc if it exists."""
        config_path = Path.home() / ".codexarc"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
        return {}
    
    def get_provider(self) -> str:
        """Get the configured AI provider."""
        return self.user_config.get("provider", self.default_provider)
    
    def get_model(self, provider: Optional[str] = None) -> str:
        """Get the model for the specified provider."""
        provider = provider or self.get_provider()
        user_models = self.user_config.get("models", {})
        return user_models.get(provider, self.default_models.get(provider))
    
    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get the API key for the specified provider."""
        provider = provider or self.get_provider()
        if provider == "openai":
            return self.openai_api_key
        elif provider == "anthropic":
            return self.anthropic_api_key
        elif provider == "openrouter":
            return self.openrouter_api_key
        return None
    
    def has_valid_config(self) -> bool:
        """Check if we have a valid configuration with API keys."""
        return bool(self.openai_api_key or self.anthropic_api_key or self.openrouter_api_key)
    
    def get_available_providers(self) -> List[str]:
        """Get list of providers with valid API keys."""
        providers = []
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic") 
        if self.openrouter_api_key:
            providers.append("openrouter")
        return providers
    
    def get_available_models(self, provider: Optional[str] = None) -> List[str]:
        """Get available models for a provider (from config)."""
        provider = provider or self.get_provider()
        user_models = self.user_config.get("models", {})
        
        if provider in user_models:
            # If it's a list, return it; if it's a string, wrap in list
            models = user_models[provider]
            if isinstance(models, list):
                return models
            else:
                return [models]
        
        # Fallback to default model
        default_model = self.default_models.get(provider)
        return [default_model] if default_model else []
    
    def switch_provider(self, provider: str) -> bool:
        """Switch to a different provider."""
        if provider not in self.get_available_providers():
            return False
        
        self.user_config["provider"] = provider
        self._save_user_config()
        return True
    
    def switch_model(self, model: str, provider: Optional[str] = None) -> bool:
        """Switch to a different model."""
        provider = provider or self.get_provider()
        
        # Update model in config
        if "models" not in self.user_config:
            self.user_config["models"] = {}
        
        self.user_config["models"][provider] = model
        self._save_user_config()
        return True
    
    def _save_user_config(self) -> None:
        """Save user configuration to file."""
        config_path = Path.home() / ".codexarc"
        try:
            with open(config_path, 'w') as f:
                yaml.dump(self.user_config, f, default_flow_style=False)
        except Exception as e:
            # Silently fail to avoid disrupting user experience
            pass
    
    def create_default_config(self) -> None:
        """Create a default .codexarc file for the user."""
        config_path = Path.home() / ".codexarc"
        default_config = {
            "provider": "openrouter",
            "models": {
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3-5-haiku-20241022",
                "openrouter": "moonshotai/kimi-k2:free"
            },
            "openrouter": {
                "site_name": "https://myapp.com",
                "app_name": "Codexa",
                "use_oai_client": True  # Use OpenAI client approach by default (True) or HTTP requests (False)
            },
            "guidelines": {
                "coding_style": "clean and readable",
                "testing": "include unit tests",
                "documentation": "comprehensive"
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)