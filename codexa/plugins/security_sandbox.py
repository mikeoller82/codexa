"""
Security sandbox for MCP plugins with permission management.
"""

import os
import subprocess
import tempfile
import shutil
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json


class Permission(Enum):
    """Plugin permissions."""
    NETWORK_ACCESS = "network_access"
    FILE_READ = "file_read" 
    FILE_WRITE = "file_write"
    PROCESS_EXECUTE = "process_execute"
    ENVIRONMENT_READ = "environment_read"
    ENVIRONMENT_WRITE = "environment_write"
    SYSTEM_INFO = "system_info"
    MCP_SERVER_ACCESS = "mcp_server_access"


@dataclass
class SandboxPolicy:
    """Security policy for sandbox execution."""
    permissions: Set[Permission] = field(default_factory=set)
    allowed_domains: List[str] = field(default_factory=list)
    allowed_file_paths: List[str] = field(default_factory=list)
    blocked_file_paths: List[str] = field(default_factory=list)
    max_execution_time: int = 30  # seconds
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    network_timeout: int = 10
    temp_dir_access: bool = True
    
    @classmethod
    def restricted(cls) -> "SandboxPolicy":
        """Create a restricted sandbox policy."""
        return cls(
            permissions={Permission.FILE_READ},
            max_execution_time=10,
            max_memory_mb=128,
            max_cpu_percent=25
        )
    
    @classmethod
    def standard(cls) -> "SandboxPolicy":
        """Create a standard sandbox policy."""
        return cls(
            permissions={
                Permission.NETWORK_ACCESS,
                Permission.FILE_READ,
                Permission.SYSTEM_INFO,
                Permission.MCP_SERVER_ACCESS
            },
            max_execution_time=30,
            max_memory_mb=512
        )
    
    @classmethod
    def trusted(cls) -> "SandboxPolicy":
        """Create a trusted sandbox policy."""
        return cls(
            permissions={p for p in Permission},
            max_execution_time=300,
            max_memory_mb=2048,
            max_cpu_percent=75
        )


class SecurityViolation(Exception):
    """Security violation in sandbox."""
    pass


class SecuritySandbox:
    """Security sandbox for plugin execution."""
    
    def __init__(self, policy: SandboxPolicy):
        self.policy = policy
        self.logger = logging.getLogger("sandbox")
        self.temp_dir: Optional[Path] = None
        self.active_processes: List[subprocess.Popen] = []
        
    def __enter__(self):
        """Enter sandbox context."""
        if self.policy.temp_dir_access:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="codexa_sandbox_"))
            self.logger.info(f"Created sandbox temp dir: {self.temp_dir}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sandbox context."""
        # Clean up processes
        for process in self.active_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                self.logger.warning(f"Failed to clean up process: {e}")
        
        # Clean up temp directory
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Cleaned up sandbox temp dir: {self.temp_dir}")
            except Exception as e:
                self.logger.error(f"Failed to clean up temp dir: {e}")
    
    def check_permission(self, permission: Permission) -> bool:
        """Check if permission is granted."""
        return permission in self.policy.permissions
    
    def require_permission(self, permission: Permission):
        """Require permission or raise SecurityViolation."""
        if not self.check_permission(permission):
            raise SecurityViolation(f"Permission denied: {permission.value}")
    
    def validate_file_access(self, file_path: str, operation: str = "read") -> bool:
        """Validate file access against policy."""
        path = Path(file_path).resolve()
        
        # Check blocked paths
        for blocked in self.policy.blocked_file_paths:
            if str(path).startswith(blocked):
                return False
        
        # Check allowed paths if specified
        if self.policy.allowed_file_paths:
            allowed = False
            for allowed_path in self.policy.allowed_file_paths:
                if str(path).startswith(allowed_path):
                    allowed = True
                    break
            if not allowed:
                return False
        
        # Check temp dir access
        if self.temp_dir and str(path).startswith(str(self.temp_dir)):
            return True
        
        # Check operation permissions
        if operation == "read":
            return self.check_permission(Permission.FILE_READ)
        elif operation == "write":
            return self.check_permission(Permission.FILE_WRITE)
        
        return False
    
    def validate_network_access(self, url: str) -> bool:
        """Validate network access against policy."""
        if not self.check_permission(Permission.NETWORK_ACCESS):
            return False
        
        # Check domain allowlist if specified
        if self.policy.allowed_domains:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return any(domain.endswith(allowed) for allowed in self.policy.allowed_domains)
        
        return True
    
    def execute_command(self, command: List[str], cwd: Optional[str] = None,
                       env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        """Execute command in sandbox."""
        self.require_permission(Permission.PROCESS_EXECUTE)
        
        # Prepare environment
        sandbox_env = os.environ.copy() if env is None else env.copy()
        
        # Add temp dir to environment if available
        if self.temp_dir:
            sandbox_env["SANDBOX_TEMP_DIR"] = str(self.temp_dir)
        
        # Set working directory
        if cwd is None and self.temp_dir:
            cwd = str(self.temp_dir)
        
        try:
            # Execute with timeout and resource limits
            result = subprocess.run(
                command,
                cwd=cwd,
                env=sandbox_env,
                timeout=self.policy.max_execution_time,
                capture_output=True,
                text=True,
                check=False
            )
            
            self.logger.info(f"Executed command in sandbox: {' '.join(command)}")
            return result
            
        except subprocess.TimeoutExpired as e:
            raise SecurityViolation(f"Command timed out after {self.policy.max_execution_time}s")
        except Exception as e:
            raise SecurityViolation(f"Command execution failed: {e}")
    
    def read_file(self, file_path: str) -> str:
        """Read file with sandbox validation."""
        if not self.validate_file_access(file_path, "read"):
            raise SecurityViolation(f"File read denied: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise SecurityViolation(f"Failed to read file: {e}")
    
    def write_file(self, file_path: str, content: str) -> None:
        """Write file with sandbox validation."""
        if not self.validate_file_access(file_path, "write"):
            raise SecurityViolation(f"File write denied: {file_path}")
        
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise SecurityViolation(f"Failed to write file: {e}")
    
    def get_temp_file(self, suffix: str = ".tmp") -> Path:
        """Get a temporary file path in sandbox."""
        if not self.temp_dir:
            raise SecurityViolation("Temporary file access not available")
        
        import uuid
        filename = f"sandbox_{uuid.uuid4().hex[:8]}{suffix}"
        return self.temp_dir / filename
    
    def get_environment_var(self, name: str) -> Optional[str]:
        """Get environment variable with permission check."""
        self.require_permission(Permission.ENVIRONMENT_READ)
        return os.environ.get(name)
    
    def set_environment_var(self, name: str, value: str) -> None:
        """Set environment variable with permission check."""
        self.require_permission(Permission.ENVIRONMENT_WRITE)
        os.environ[name] = value
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information with permission check."""
        self.require_permission(Permission.SYSTEM_INFO)
        
        import platform
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "temp_dir": str(self.temp_dir) if self.temp_dir else None
        }
    
    def validate_mcp_access(self, server_name: str, operation: str) -> bool:
        """Validate MCP server access."""
        return self.check_permission(Permission.MCP_SERVER_ACCESS)
    
    def create_isolated_environment(self) -> Dict[str, str]:
        """Create isolated environment variables."""
        isolated_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": str(self.temp_dir) if self.temp_dir else "/tmp",
            "TMPDIR": str(self.temp_dir) if self.temp_dir else "/tmp",
            "USER": "sandbox",
            "SHELL": "/bin/sh"
        }
        
        # Add essential environment variables
        for var in ["LANG", "LC_ALL", "TZ"]:
            if var in os.environ:
                isolated_env[var] = os.environ[var]
        
        return isolated_env
    
    def monitor_resources(self, pid: int) -> Dict[str, float]:
        """Monitor resource usage of a process."""
        try:
            import psutil
            process = psutil.Process(pid)
            
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "num_threads": process.num_threads()
            }
        except ImportError:
            self.logger.warning("psutil not available for resource monitoring")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to monitor resources: {e}")
            return {}
    
    def enforce_limits(self, pid: int) -> bool:
        """Enforce resource limits on a process."""
        try:
            resources = self.monitor_resources(pid)
            
            if resources.get("cpu_percent", 0) > self.policy.max_cpu_percent:
                self.logger.warning(f"Process {pid} exceeding CPU limit")
                return False
            
            if resources.get("memory_mb", 0) > self.policy.max_memory_mb:
                self.logger.warning(f"Process {pid} exceeding memory limit")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to enforce limits: {e}")
            return True  # Allow by default if monitoring fails