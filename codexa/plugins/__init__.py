"""
Plugin architecture for Codexa with security sandboxing.
"""

from .plugin_manager import PluginManager, Plugin, PluginInfo
from .security_sandbox import SecuritySandbox, SandboxPolicy

__all__ = [
    "PluginManager",
    "Plugin", 
    "PluginInfo",
    "SecuritySandbox",
    "SandboxPolicy"
]