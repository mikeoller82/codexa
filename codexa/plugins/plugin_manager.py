"""
Plugin manager for Codexa with security sandboxing and lifecycle management.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
import importlib.util
import sys

from .security_sandbox import SecuritySandbox, SandboxPolicy, SecurityViolation, Permission


@dataclass
class PluginInfo:
    """Plugin metadata and information."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    homepage: str = ""
    license: str = ""
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    min_codexa_version: str = "1.0.0"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginInfo":
        """Create PluginInfo from dictionary."""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "license": self.license,
            "dependencies": self.dependencies,
            "capabilities": self.capabilities,
            "permissions": self.permissions,
            "mcp_servers": self.mcp_servers,
            "commands": self.commands,
            "min_codexa_version": self.min_codexa_version
        }
    
    def requires_permission(self, permission: Permission) -> bool:
        """Check if plugin requires a specific permission."""
        return permission.value in self.permissions


class Plugin(ABC):
    """Base class for Codexa plugins."""
    
    def __init__(self, info: PluginInfo):
        self.info = info
        self.enabled = False
        self.sandbox: Optional[SecuritySandbox] = None
        self.logger = logging.getLogger(f"plugin.{info.name}")
    
    @abstractmethod
    async def initialize(self, context: Dict[str, Any]) -> bool:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown the plugin."""
        pass
    
    async def on_command(self, command: str, args: Dict[str, Any]) -> Optional[str]:
        """Handle plugin-specific commands."""
        return None
    
    async def on_mcp_request(self, server: str, request: str, context: Dict[str, Any]) -> Optional[Any]:
        """Handle MCP server requests."""
        return None
    
    async def on_provider_switch(self, old_provider: str, new_provider: str) -> None:
        """Handle provider switch events."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get plugin status."""
        return {
            "name": self.info.name,
            "version": self.info.version,
            "enabled": self.enabled,
            "sandbox_active": self.sandbox is not None
        }


class PluginLoadError(Exception):
    """Plugin loading error."""
    pass


class PluginManager:
    """Manager for Codexa plugins with security sandboxing."""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_infos: Dict[str, PluginInfo] = {}
        self.sandbox_policies: Dict[str, SandboxPolicy] = {}
        self.plugin_directories: List[Path] = []
        self.logger = logging.getLogger("plugin_manager")
        
        # Plugin lifecycle hooks
        self.lifecycle_hooks: Dict[str, List[callable]] = {
            "before_load": [],
            "after_load": [],
            "before_enable": [],
            "after_enable": [],
            "before_disable": [],
            "after_disable": []
        }
        
        # Default plugin directory
        self.add_plugin_directory(Path(__file__).parent.parent / "plugins" / "available")
    
    def add_plugin_directory(self, path: Path):
        """Add a directory to search for plugins."""
        if path.exists() and path.is_dir():
            self.plugin_directories.append(path)
            self.logger.info(f"Added plugin directory: {path}")
    
    def discover_plugins(self) -> List[PluginInfo]:
        """Discover available plugins in plugin directories."""
        discovered = []
        
        for directory in self.plugin_directories:
            for plugin_path in directory.iterdir():
                if plugin_path.is_dir():
                    try:
                        info = self._load_plugin_info(plugin_path)
                        if info:
                            discovered.append(info)
                    except Exception as e:
                        self.logger.error(f"Failed to load plugin info from {plugin_path}: {e}")
        
        return discovered
    
    def _load_plugin_info(self, plugin_path: Path) -> Optional[PluginInfo]:
        """Load plugin info from plugin directory."""
        manifest_path = plugin_path / "plugin.json"
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            info = PluginInfo.from_dict(data)
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to parse plugin manifest: {e}")
            return None
    
    async def load_plugin(self, plugin_path: Path, sandbox_policy: Optional[SandboxPolicy] = None) -> bool:
        """Load a plugin from path with sandboxing."""
        try:
            # Load plugin info
            info = self._load_plugin_info(plugin_path)
            if not info:
                raise PluginLoadError(f"Invalid plugin manifest: {plugin_path}")
            
            # Check if already loaded
            if info.name in self.plugins:
                self.logger.warning(f"Plugin {info.name} already loaded")
                return False
            
            # Run before_load hooks
            await self._run_lifecycle_hooks("before_load", info)
            
            # Determine sandbox policy
            if sandbox_policy is None:
                sandbox_policy = self._determine_sandbox_policy(info)
            
            # Load plugin code
            plugin = await self._load_plugin_code(plugin_path, info)
            if not plugin:
                raise PluginLoadError(f"Failed to load plugin code: {info.name}")
            
            # Store plugin and info
            self.plugins[info.name] = plugin
            self.plugin_infos[info.name] = info
            self.sandbox_policies[info.name] = sandbox_policy
            
            # Run after_load hooks
            await self._run_lifecycle_hooks("after_load", info)
            
            self.logger.info(f"Loaded plugin: {info.name} v{info.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            return False
    
    def _determine_sandbox_policy(self, info: PluginInfo) -> SandboxPolicy:
        """Determine sandbox policy based on plugin info."""
        # Convert permission strings to Permission enums
        permissions = set()
        for perm_str in info.permissions:
            try:
                permissions.add(Permission(perm_str))
            except ValueError:
                self.logger.warning(f"Unknown permission: {perm_str}")
        
        # Determine policy level based on permissions
        if Permission.PROCESS_EXECUTE in permissions or Permission.ENVIRONMENT_WRITE in permissions:
            policy = SandboxPolicy.trusted()
        elif Permission.FILE_WRITE in permissions or Permission.NETWORK_ACCESS in permissions:
            policy = SandboxPolicy.standard()
        else:
            policy = SandboxPolicy.restricted()
        
        # Apply specific permissions
        policy.permissions = permissions
        
        return policy
    
    async def _load_plugin_code(self, plugin_path: Path, info: PluginInfo) -> Optional[Plugin]:
        """Load plugin code from Python file."""
        main_file = plugin_path / "main.py"
        if not main_file.exists():
            self.logger.error(f"Plugin main.py not found: {plugin_path}")
            return None
        
        try:
            # Load module
            spec = importlib.util.spec_from_file_location(f"plugin_{info.name}", main_file)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find Plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr != Plugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                self.logger.error(f"No Plugin class found in {main_file}")
                return None
            
            # Instantiate plugin
            plugin = plugin_class(info)
            return plugin
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin code: {e}")
            return None
    
    async def enable_plugin(self, name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Enable a loaded plugin."""
        if name not in self.plugins:
            self.logger.error(f"Plugin not loaded: {name}")
            return False
        
        plugin = self.plugins[name]
        if plugin.enabled:
            self.logger.warning(f"Plugin already enabled: {name}")
            return True
        
        try:
            info = self.plugin_infos[name]
            policy = self.sandbox_policies[name]
            
            # Run before_enable hooks
            await self._run_lifecycle_hooks("before_enable", info)
            
            # Create sandbox
            plugin.sandbox = SecuritySandbox(policy)
            
            # Initialize plugin with sandbox
            with plugin.sandbox:
                success = await plugin.initialize(context or {})
            
            if success:
                plugin.enabled = True
                await self._run_lifecycle_hooks("after_enable", info)
                self.logger.info(f"Enabled plugin: {name}")
                return True
            else:
                plugin.sandbox = None
                self.logger.error(f"Plugin initialization failed: {name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to enable plugin {name}: {e}")
            if plugin.sandbox:
                plugin.sandbox = None
            return False
    
    async def disable_plugin(self, name: str) -> bool:
        """Disable an enabled plugin."""
        if name not in self.plugins:
            return False
        
        plugin = self.plugins[name]
        if not plugin.enabled:
            return True
        
        try:
            info = self.plugin_infos[name]
            
            # Run before_disable hooks
            await self._run_lifecycle_hooks("before_disable", info)
            
            # Shutdown plugin
            if plugin.sandbox:
                with plugin.sandbox:
                    await plugin.shutdown()
                plugin.sandbox = None
            
            plugin.enabled = False
            
            # Run after_disable hooks
            await self._run_lifecycle_hooks("after_disable", info)
            
            self.logger.info(f"Disabled plugin: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable plugin {name}: {e}")
            return False
    
    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin completely."""
        if name not in self.plugins:
            return False
        
        # Disable first
        await self.disable_plugin(name)
        
        # Remove from registry
        del self.plugins[name]
        del self.plugin_infos[name]
        del self.sandbox_policies[name]
        
        self.logger.info(f"Unloaded plugin: {name}")
        return True
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin instance."""
        return self.plugins.get(name)
    
    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugin names."""
        return [name for name, plugin in self.plugins.items() if plugin.enabled]
    
    def get_plugin_info(self, name: str) -> Optional[PluginInfo]:
        """Get plugin information."""
        return self.plugin_infos.get(name)
    
    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded plugins with status."""
        result = {}
        for name, plugin in self.plugins.items():
            info = self.plugin_infos[name]
            result[name] = {
                "info": info.to_dict(),
                "status": plugin.get_status(),
                "sandbox_policy": str(self.sandbox_policies[name])
            }
        return result
    
    async def execute_plugin_command(self, plugin_name: str, command: str, 
                                   args: Dict[str, Any]) -> Optional[str]:
        """Execute a plugin-specific command."""
        plugin = self.get_plugin(plugin_name)
        if not plugin or not plugin.enabled:
            return None
        
        try:
            if plugin.sandbox:
                with plugin.sandbox:
                    return await plugin.on_command(command, args)
            else:
                return await plugin.on_command(command, args)
                
        except SecurityViolation as e:
            self.logger.error(f"Security violation in plugin {plugin_name}: {e}")
            return f"Security violation: {e}"
        except Exception as e:
            self.logger.error(f"Plugin command error in {plugin_name}: {e}")
            return f"Plugin error: {e}"
    
    async def handle_mcp_request(self, server: str, request: str, 
                               context: Dict[str, Any]) -> List[Any]:
        """Handle MCP requests through enabled plugins."""
        results = []
        
        for name, plugin in self.plugins.items():
            if not plugin.enabled:
                continue
            
            try:
                if plugin.sandbox:
                    with plugin.sandbox:
                        result = await plugin.on_mcp_request(server, request, context)
                else:
                    result = await plugin.on_mcp_request(server, request, context)
                
                if result is not None:
                    results.append({
                        "plugin": name,
                        "result": result
                    })
                    
            except SecurityViolation as e:
                self.logger.error(f"Security violation in plugin {name}: {e}")
            except Exception as e:
                self.logger.error(f"Plugin MCP request error in {name}: {e}")
        
        return results
    
    async def notify_provider_switch(self, old_provider: str, new_provider: str):
        """Notify all enabled plugins of provider switch."""
        for plugin in self.plugins.values():
            if plugin.enabled:
                try:
                    await plugin.on_provider_switch(old_provider, new_provider)
                except Exception as e:
                    self.logger.error(f"Plugin provider switch notification error: {e}")
    
    def add_lifecycle_hook(self, event: str, hook: callable):
        """Add lifecycle hook."""
        if event in self.lifecycle_hooks:
            self.lifecycle_hooks[event].append(hook)
    
    async def _run_lifecycle_hooks(self, event: str, info: PluginInfo):
        """Run lifecycle hooks for an event."""
        for hook in self.lifecycle_hooks.get(event, []):
            try:
                await hook(info)
            except Exception as e:
                self.logger.error(f"Lifecycle hook error for {event}: {e}")
    
    async def initialize_plugins(self) -> bool:
        """Initialize plugin system by discovering and loading available plugins."""
        try:
            self.logger.info("Initializing plugin system...")
            
            # Discover available plugins
            discovered_plugins = self.discover_plugins()
            self.logger.info(f"Discovered {len(discovered_plugins)} plugins")
            
            # Load discovered plugins
            loaded_count = 0
            for plugin_info in discovered_plugins:
                # Find plugin directory
                plugin_path = None
                for directory in self.plugin_directories:
                    candidate_path = directory / plugin_info.name
                    if candidate_path.exists():
                        plugin_path = candidate_path
                        break
                
                if plugin_path:
                    success = await self.load_plugin(plugin_path)
                    if success:
                        loaded_count += 1
                        # Auto-enable plugins that don't require special permissions
                        if not plugin_info.permissions or all(perm in ['FILE_READ', 'BASIC_LOGGING'] for perm in plugin_info.permissions):
                            await self.enable_plugin(plugin_info.name)
            
            self.logger.info(f"Plugin system initialized: {loaded_count} plugins loaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin system: {e}")
            return False

    def get_plugin_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics."""
        return {
            "total_plugins": len(self.plugins),
            "enabled_plugins": len(self.get_enabled_plugins()),
            "plugin_directories": len(self.plugin_directories),
            "sandbox_policies": len(self.sandbox_policies)
        }