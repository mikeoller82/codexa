"""
Enhanced configuration management for Codexa with multi-model and MCP support.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
import yaml
from dotenv import load_dotenv
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: str
    enabled: bool = True
    max_tokens: int = 2048
    temperature: float = 0.3
    timeout: int = 30
    cost_per_token: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str
    api_key_env: str
    base_url: Optional[str] = None
    enabled: bool = True
    priority: int = 1  # Higher = preferred
    models: List[ModelConfig] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPServerConfig:
    """Configuration for MCP servers."""
    name: str
    command: List[str]
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout: int = 30
    priority: int = 1
    capabilities: List[str] = field(default_factory=list)


class EnhancedConfig:
    """Enhanced configuration manager for Codexa."""

    def __init__(self):
        """Initialize configuration with environment variables and config files."""
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Legacy API key support
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Enhanced multi-provider configuration
        self.providers = self._initialize_providers()
        self.models = self._initialize_models()
        self.mcp_servers = self._initialize_mcp_servers()
        
        # Runtime state
        self.current_provider = None
        self.current_model = None
        self.available_providers = []
        self.available_models = []
        
        # Load user config if it exists
        self.user_config = self._load_user_config()
        
        # Apply user configuration
        self._apply_user_config()
        
        # OpenRouter preferences  
        openrouter_config = self.user_config.get("openrouter", {})
        self.openrouter_use_oai_client = openrouter_config.get("use_oai_client", True)
        
        # Initialize runtime state
        self._update_availability()
    
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
        """Get the current AI provider."""
        if self.current_provider:
            return self.current_provider
        
        # Try user config first
        user_provider = self.user_config.get("provider")
        if user_provider and self.is_provider_available(user_provider):
            self.current_provider = user_provider
            return user_provider
        
        # Fallback to first available provider
        for provider_name in self.available_providers:
            if self.is_provider_available(provider_name):
                self.current_provider = provider_name
                return provider_name
        
        return "openai"  # Final fallback
    
    def get_model(self, provider: Optional[str] = None) -> str:
        """Get the model for the specified provider."""
        provider = provider or self.get_provider()
        
        if self.current_model and self.current_provider == provider:
            return self.current_model
        
        # Try user preference first (including dynamically discovered models)
        user_models = self.user_config.get("models", {})
        preferred_model = user_models.get(provider)
        
        if preferred_model:
            # Check if it's in static config first
            available_models = self.get_available_models(provider)
            if preferred_model in available_models:
                self.current_model = preferred_model
                return preferred_model
            
            # Note: Dynamic model validation is deferred to avoid circular dependencies
            # during config initialization. The model will be validated when actually used.
            # For now, trust the user's saved preference and use it
            self.current_model = preferred_model
            return preferred_model
        
        # Fallback to static models
        available_models = self.get_available_models(provider)
        if not available_models:
            return "gpt-4o-mini"  # Final fallback
        
        # Return first available model
        self.current_model = available_models[0]
        return available_models[0]
    
    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get the API key for the specified provider."""
        provider = provider or self.get_provider()
        if provider in self.providers:
            return os.getenv(self.providers[provider].api_key_env)
        
        # Legacy fallback
        if provider == "openai":
            return self.openai_api_key
        elif provider == "anthropic":
            return self.anthropic_api_key
        elif provider == "openrouter":
            return self.openrouter_api_key
        return None
    
    def has_valid_config(self) -> bool:
        """Check if we have a valid configuration with API keys."""
        return len(self.available_providers) > 0
    
    def create_default_config(self) -> None:
        """Create a default .codexarc file with enhanced configuration."""
        config_path = Path.home() / ".codexarc"
        default_config = {
            "provider": "openai",
            "models": {
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3-5-haiku-20241022",
                "openrouter": "openrouter/sonoma-sky-alpha"
            },
            "providers": {
                "openai": {
                    "enabled": True,
                    "priority": 1,
                    "timeout": 30
                },
                "anthropic": {
                    "enabled": True,
                    "priority": 2,
                    "timeout": 30
                },
                "openrouter": {
                    "enabled": True,
                    "priority": 3,
                    "timeout": 30,
                    "site_name": "https://myapp.com",
                    "app_name": "Codexa"
                }
            },
            "mcp_servers": {
                "serena": {
                    "command": ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"],
                    "args": ["--context", "ide-assistant", "--project", "."],
                    "enabled": False,
                    "timeout": 30,
                    "project_path": None,  # Set to activate a specific project
                    "auto_index": True,
                    "deployment_mode": "uvx"  # Options: uvx, local, docker
                },
                "context7": {
                    "command": ["npx", "-y", "@modelcontextprotocol/server-context7"],
                    "enabled": False,
                    "timeout": 30
                },
                "sequential": {
                    "command": ["python", "-m", "sequential_server"],
                    "enabled": False,
                    "timeout": 30
                }
            },
            "slash_commands": {
                "enabled": True,
                "custom_commands": {}
            },
            "display": {
                "ascii_logo": True,
                "animations": True,
                "colors": True,
                "theme": "default"
            },
            "guidelines": {
                "coding_style": "clean and readable",
                "testing": "include unit tests",
                "documentation": "comprehensive"
            },
            "features": {
                "slash_commands": True,
                "ascii_logo": True,
                "provider_switching": True,
                "model_switching": True,
                "mcp_integration": True
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    def _initialize_providers(self) -> Dict[str, ProviderConfig]:
        """Initialize default provider configurations."""
        return {
            "openai": ProviderConfig(
                name="openai",
                api_key_env="OPENAI_API_KEY",
                priority=1,
                models=[
                    ModelConfig("gpt-4o", "openai", capabilities=["code", "analysis", "reasoning"]),
                    ModelConfig("gpt-4o-mini", "openai", capabilities=["code", "analysis"]),
                    ModelConfig("o1-preview", "openai", capabilities=["reasoning", "complex_analysis"]),
                    ModelConfig("o1-mini", "openai", capabilities=["reasoning"])
                ]
            ),
            "anthropic": ProviderConfig(
                name="anthropic", 
                api_key_env="ANTHROPIC_API_KEY",
                priority=2,
                models=[
                    ModelConfig("claude-3-5-sonnet-20241022", "anthropic", capabilities=["code", "analysis", "reasoning"]),
                    ModelConfig("claude-3-5-haiku-20241022", "anthropic", capabilities=["code", "analysis"]),
                    ModelConfig("claude-3-opus-20240229", "anthropic", capabilities=["code", "analysis", "complex_reasoning"])
                ]
            ),
            "openrouter": ProviderConfig(
                name="openrouter",
                api_key_env="OPENROUTER_API_KEY", 
                base_url="https://openrouter.ai/api/v1",
                priority=3,
                models=[
                    ModelConfig("openrouter/sonoma-sky-alpha", "openrouter", capabilities=["code", "analysis", "tools", "reasoning"]),
                    ModelConfig("deepseek/deepseek-chat-v3.1:free", "openrouter", capabilities=["code", "analysis", "tools", "reasoning"]),
                    ModelConfig("qwen/qwen3-coder:free", "openrouter", capabilities=["code", "analysis", "tools", "reasoning"]),
                    ModelConfig("moonshotai/kimi-k2:free", "openrouter", capabilities=["code", "analysis", "tools"]),
                    ModelConfig("google/gemini-2.0-flash-exp:free", "openrouter", capabilities=["code", "analysis"]),
                    ModelConfig("qwen/qwen3-235b-a22b:free", "openrouter", capabilities=["code", "analysis"]),
                    ModelConfig("meta-llama/llama-4-maverick:free", "openrouter", capabilities=["code", "analysis"])
                ]
            )
        }
    
    def _initialize_models(self) -> Dict[str, ModelConfig]:
        """Initialize model configurations from providers."""
        models = {}
        for provider in self.providers.values():
            for model in provider.models:
                models[f"{provider.name}:{model.name}"] = model
        return models
    
    def _initialize_mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Initialize MCP server configurations."""
        return {
            "filesystem": MCPServerConfig(
                name="filesystem",
                command=["/home/mike/go/bin/mcp-filesystem-server"],
                args=["/home/mike/codexa", "/tmp", "/var/tmp", str(Path.cwd())],  # Allow current directory and common paths
                enabled=True,  # Always enabled by default for core filesystem operations
                capabilities=["filesystem", "file_operations", "directory_operations", "file_search"],
                priority=10,  # High priority for core operations
                timeout=10  # Reasonable timeout for filesystem operations
            ),
            "serena": MCPServerConfig(
                name="serena",
                command=["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"],
                args=["--context", "ide-assistant", "--project", "."],
                enabled=True,  # Enabled by default for Serena integration
                capabilities=[
                    "semantic-analysis", "code-editing", "symbol-search", "language-server",
                    "project-management", "shell-execution", "memory", "onboarding",
                    "file-operations", "pattern-search", "code-refactoring"
                ],
                priority=5,  # High priority for semantic operations
                timeout=30  # Reasonable timeout for language server operations
            ),
            "context7": MCPServerConfig(
                name="context7",
                command=["npx", "-y", "@modelcontextprotocol/server-context7"],
                enabled=False,
                capabilities=["documentation", "search", "examples"]
            ),
            "sequential": MCPServerConfig(
                name="sequential",
                command=["python", "-m", "sequential_server"],
                enabled=False,
                capabilities=["reasoning", "analysis", "planning"]
            ),
            "magic": MCPServerConfig(
                name="magic",
                command=["python", "-m", "magic_server"],
                enabled=False,
                capabilities=["ui_generation", "components", "design"]
            )
        }
    
    def _apply_user_config(self):
        """Apply user configuration overrides."""
        if not self.user_config:
            return
        
        # Update provider configurations
        if "providers" in self.user_config:
            for name, config in self.user_config["providers"].items():
                if name in self.providers:
                    provider = self.providers[name]
                    provider.enabled = config.get("enabled", provider.enabled)
                    provider.priority = config.get("priority", provider.priority)
                    provider.metadata.update(config)
        
        # Update MCP server configurations
        if "mcp_servers" in self.user_config:
            for name, config in self.user_config["mcp_servers"].items():
                if name in self.mcp_servers:
                    server = self.mcp_servers[name]
                    server.enabled = config.get("enabled", server.enabled)
                    server.command = config.get("command", server.command)
                    server.args = config.get("args", server.args)
    
    def _update_availability(self):
        """Update available providers and models based on API keys."""
        self.available_providers = []
        self.available_models = []
        
        for name, provider in self.providers.items():
            if provider.enabled and os.getenv(provider.api_key_env):
                self.available_providers.append(name)
                
                # Add models for this provider
                for model in provider.models:
                    if model.enabled:
                        self.available_models.append(model.name)
        
        # Sort by priority
        self.available_providers.sort(key=lambda x: self.providers[x].priority)
    
    def is_provider_available(self, provider_name: str) -> bool:
        """Check if provider is available (has API key)."""
        return provider_name in self.available_providers
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return self.available_providers.copy()
    
    def get_available_models(self, provider: Optional[str] = None) -> List[str]:
        """Get available models for provider."""
        if provider and provider in self.providers:
            provider_obj = self.providers[provider]
            if provider_obj.enabled and os.getenv(provider_obj.api_key_env):
                return [m.name for m in provider_obj.models if m.enabled]
        return []
    
    def switch_provider(self, provider_name: str) -> bool:
        """Switch to different provider and persist the selection."""
        if not self.is_provider_available(provider_name):
            return False
        
        # Update runtime state
        self.current_provider = provider_name
        self.current_model = None  # Reset model selection
        
        # Persist to user config
        try:
            self.user_config["provider"] = provider_name
            self.save_config()
            return True
        except Exception as e:
            # If saving fails, still update runtime state but report the issue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save provider selection to config: {e}")
            return False
    
    def switch_model(self, model_name: str, provider: Optional[str] = None) -> bool:
        """Switch to different model and persist the selection."""
        provider = provider or self.current_provider
        if not provider:
            return False
        
        # Check if model is available in static config
        available_models = self.get_available_models(provider)
        model_available_statically = model_name in available_models
        
        # Note: Dynamic model validation is deferred to avoid circular dependencies
        # If not in static config, we'll accept it and validate later when used
        if not model_available_statically:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Model '{model_name}' not in static config, will validate when used")
        
        # Update runtime state
        self.current_model = model_name
        
        # Persist to user config
        try:
            if "models" not in self.user_config:
                self.user_config["models"] = {}
            
            self.user_config["models"][provider] = model_name
            
            # Also update provider if it changed
            if provider != self.current_provider:
                self.current_provider = provider
                self.user_config["provider"] = provider
            
            # Save the config immediately
            self.save_config()
            return True
        except Exception as e:
            # If saving fails, still update runtime state but report the issue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save model selection to config: {e}")
            return False
    
    def get_model_config(self, model_name: str, provider: Optional[str] = None) -> Optional[ModelConfig]:
        """Get detailed model configuration."""
        provider = provider or self.current_provider
        if not provider or provider not in self.providers:
            return None
        
        for model in self.providers[provider].models:
            if model.name == model_name:
                return model
        return None
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get detailed provider configuration."""
        return self.providers.get(provider_name)
    
    def get_mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Get enabled MCP server configurations."""
        # Always ensure filesystem server is properly configured
        self.ensure_filesystem_server_enabled()
        return {k: v for k, v in self.mcp_servers.items() if v.enabled}
    
    def ensure_filesystem_server_enabled(self) -> bool:
        """Ensure the MCP filesystem server is enabled and properly configured."""
        try:
            if "filesystem" in self.mcp_servers:
                # Update args to include current working directory
                fs_server = self.mcp_servers["filesystem"]
                current_dir = str(Path.cwd())
                
                # Ensure current directory is in allowed paths
                if current_dir not in fs_server.args:
                    fs_server.args.append(current_dir)
                
                # Ensure it's enabled
                fs_server.enabled = True
                
                # Update user config to persist this
                user_mcp = self.user_config.setdefault("mcp_servers", {})
                user_mcp.setdefault("filesystem", {})["enabled"] = True
                
                return True
            return False
        except Exception as e:
            # Use print instead of logger to avoid circular imports
            print(f"Warning: Failed to ensure filesystem server enabled: {e}")
            return False
    
    def enable_feature(self, feature_name: str, enabled: bool = True):
        """Enable/disable a feature."""
        if "features" not in self.user_config:
            self.user_config["features"] = {}
        self.user_config["features"][feature_name] = enabled
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if feature is enabled."""
        return self.user_config.get("features", {}).get(feature_name, True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive configuration status."""
        return {
            "current_provider": self.current_provider,
            "current_model": self.current_model,
            "available_providers": self.available_providers,
            "total_models": len(self.available_models),
            "mcp_servers_enabled": len([s for s in self.mcp_servers.values() if s.enabled]),
            "features": self.user_config.get("features", {}),
            "config_file_exists": (Path.home() / ".codexarc").exists()
        }
    
    def validate_mcp_server_config(self, server_name: str, config: Dict[str, Any]) -> bool:
        """Validate MCP server configuration."""
        required_fields = ["command"]
        optional_fields = ["args", "env", "enabled", "timeout", "priority", "capabilities"]
        
        # Check required fields
        for field in required_fields:
            if field not in config:
                raise ValueError(f"MCP server '{server_name}' missing required field: {field}")
        
        # Validate command is a list
        if not isinstance(config["command"], list):
            raise ValueError(f"MCP server '{server_name}' command must be a list")
        
        # Set defaults for optional fields
        config.setdefault("args", [])
        config.setdefault("env", {})
        config.setdefault("enabled", False)
        config.setdefault("timeout", 30)
        config.setdefault("priority", 1)
        config.setdefault("capabilities", [])
        
        # Validate types
        if not isinstance(config["args"], list):
            raise ValueError(f"MCP server '{server_name}' args must be a list")
        if not isinstance(config["env"], dict):
            raise ValueError(f"MCP server '{server_name}' env must be a dict")
        if not isinstance(config["enabled"], bool):
            raise ValueError(f"MCP server '{server_name}' enabled must be a boolean")
        if not isinstance(config["timeout"], int) or config["timeout"] <= 0:
            raise ValueError(f"MCP server '{server_name}' timeout must be a positive integer")
        if not isinstance(config["priority"], int):
            raise ValueError(f"MCP server '{server_name}' priority must be an integer")
        if not isinstance(config["capabilities"], list):
            raise ValueError(f"MCP server '{server_name}' capabilities must be a list")
        
        return True
    
    def enable_mcp_server(self, server_name: str) -> bool:
        """Enable an MCP server with validation."""
        if "mcp_servers" not in self.user_config:
            self.user_config["mcp_servers"] = {}
        
        # Check if server exists in config
        if server_name not in self.user_config["mcp_servers"]:
            # Add default configuration from built-in servers
            if server_name in self.mcp_servers:
                default_config = {
                    "command": self.mcp_servers[server_name].command,
                    "args": self.mcp_servers[server_name].args,
                    "env": self.mcp_servers[server_name].env,
                    "enabled": True,
                    "timeout": self.mcp_servers[server_name].timeout,
                    "priority": self.mcp_servers[server_name].priority,
                    "capabilities": self.mcp_servers[server_name].capabilities
                }
                self.user_config["mcp_servers"][server_name] = default_config
            else:
                raise ValueError(f"Unknown MCP server: {server_name}")
        
        # Validate configuration
        try:
            self.validate_mcp_server_config(server_name, self.user_config["mcp_servers"][server_name])
        except ValueError as e:
            raise ValueError(f"Invalid MCP server configuration: {e}")
        
        # Enable the server
        self.user_config["mcp_servers"][server_name]["enabled"] = True
        
        # Update runtime configuration
        if server_name in self.mcp_servers:
            self.mcp_servers[server_name].enabled = True
        
        return True
    
    def disable_mcp_server(self, server_name: str) -> bool:
        """Disable an MCP server."""
        if "mcp_servers" not in self.user_config:
            return False
        
        if server_name not in self.user_config["mcp_servers"]:
            return False
        
        # Disable the server
        self.user_config["mcp_servers"][server_name]["enabled"] = False
        
        # Update runtime configuration
        if server_name in self.mcp_servers:
            self.mcp_servers[server_name].enabled = False
        
        return True
    
    def get_mcp_server_status(self) -> Dict[str, Any]:
        """Get status of all MCP servers."""
        status = {}
        for name, server in self.mcp_servers.items():
            user_config = self.user_config.get("mcp_servers", {}).get(name, {})
            status[name] = {
                "enabled": server.enabled,
                "configured": name in self.user_config.get("mcp_servers", {}),
                "command": server.command,
                "capabilities": server.capabilities,
                "priority": server.priority,
                "timeout": server.timeout
            }
        return status

    def save_config(self):
        """Save current configuration to file."""
        config_path = Path.home() / ".codexarc"
        with open(config_path, 'w') as f:
            yaml.dump(self.user_config, f, default_flow_style=False, indent=2)