"""
Health monitoring system for MCP servers.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .connection_manager import MCPConnectionManager, ConnectionState
from .protocol import MCPProtocol, MCPError


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class HealthMetrics:
    """Health metrics for a server."""
    status: HealthStatus = HealthStatus.UNKNOWN
    response_time: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    uptime: timedelta = field(default_factory=lambda: timedelta())
    last_check: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    failed_requests: int = 0


@dataclass
class HealthCheck:
    """Health check configuration."""
    name: str
    interval: int = 30  # seconds
    timeout: int = 10   # seconds
    max_failures: int = 3
    enabled: bool = True
    check_function: Optional[Callable] = None


class MCPHealthMonitor:
    """Health monitoring system for MCP servers."""
    
    def __init__(self, connection_manager: MCPConnectionManager):
        self.connection_manager = connection_manager
        self.logger = logging.getLogger("mcp.health")
        
        # Health data
        self.server_health: Dict[str, HealthMetrics] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.alert_callbacks: List[Callable[[str, HealthStatus, str], None]] = []
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.check_interval = 30  # Default interval in seconds
        
        self._initialize_default_checks()
    
    def _initialize_default_checks(self):
        """Initialize default health checks."""
        
        # Basic connectivity check
        self.health_checks["connectivity"] = HealthCheck(
            name="connectivity",
            interval=30,
            timeout=10,
            max_failures=3,
            check_function=self._check_connectivity
        )
        
        # Response time check
        self.health_checks["response_time"] = HealthCheck(
            name="response_time", 
            interval=60,
            timeout=15,
            max_failures=2,
            check_function=self._check_response_time
        )
        
        # Capability check
        self.health_checks["capabilities"] = HealthCheck(
            name="capabilities",
            interval=300,  # 5 minutes
            timeout=20,
            max_failures=1,
            check_function=self._check_capabilities
        )
    
    async def start_monitoring(self):
        """Start health monitoring."""
        if self.monitoring_active:
            self.logger.warning("Health monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        self.logger.info("Health monitoring stopped")
    
    def add_server(self, server_name: str):
        """Add server to health monitoring."""
        if server_name not in self.server_health:
            self.server_health[server_name] = HealthMetrics()
            self.logger.info(f"Added server to health monitoring: {server_name}")
    
    def remove_server(self, server_name: str):
        """Remove server from health monitoring."""
        if server_name in self.server_health:
            del self.server_health[server_name]
            self.logger.info(f"Removed server from health monitoring: {server_name}")
    
    def get_server_health(self, server_name: str) -> Optional[HealthMetrics]:
        """Get health metrics for a server."""
        return self.server_health.get(server_name)
    
    def get_all_health(self) -> Dict[str, HealthMetrics]:
        """Get health metrics for all servers."""
        return self.server_health.copy()
    
    def add_alert_callback(self, callback: Callable[[str, HealthStatus, str], None]):
        """Add callback for health alerts."""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable):
        """Remove alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._run_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _run_health_checks(self):
        """Run health checks for all servers."""
        available_servers = self.connection_manager.get_available_servers()
        
        # Add new servers to monitoring
        for server_name in available_servers:
            if server_name not in self.server_health:
                self.add_server(server_name)
        
        # Run checks for each server
        check_tasks = []
        for server_name in self.server_health.keys():
            task = asyncio.create_task(self._check_server_health(server_name))
            check_tasks.append(task)
        
        if check_tasks:
            await asyncio.gather(*check_tasks, return_exceptions=True)
    
    async def _check_server_health(self, server_name: str):
        """Check health for a specific server."""
        metrics = self.server_health[server_name]
        current_time = datetime.now()
        
        # Skip if server is not available
        if server_name not in self.connection_manager.get_available_servers():
            self._update_server_status(server_name, HealthStatus.DOWN, "Server not available")
            return
        
        # Run enabled health checks
        check_results = []
        for check_name, check in self.health_checks.items():
            if not check.enabled:
                continue
            
            # Check if it's time to run this check
            if (metrics.last_check and 
                (current_time - metrics.last_check).seconds < check.interval):
                continue
            
            try:
                result = await self._run_single_check(server_name, check)
                check_results.append((check_name, result))
            except Exception as e:
                self.logger.error(f"Health check '{check_name}' failed for {server_name}: {e}")
                check_results.append((check_name, False))
        
        # Update metrics based on check results
        self._process_check_results(server_name, check_results)
        
        # Update last check time
        metrics.last_check = current_time
    
    async def _run_single_check(self, server_name: str, check: HealthCheck) -> bool:
        """Run a single health check."""
        if check.check_function:
            try:
                result = await asyncio.wait_for(
                    check.check_function(server_name),
                    timeout=check.timeout
                )
                return result
            except asyncio.TimeoutError:
                self.logger.warning(f"Health check '{check.name}' timed out for {server_name}")
                return False
            except Exception as e:
                self.logger.error(f"Health check '{check.name}' error for {server_name}: {e}")
                return False
        return True
    
    def _process_check_results(self, server_name: str, results: List[tuple]):
        """Process health check results and update metrics."""
        metrics = self.server_health[server_name]
        
        # Calculate overall health
        total_checks = len(results)
        passed_checks = sum(1 for _, result in results if result)
        
        if total_checks == 0:
            return
        
        success_rate = passed_checks / total_checks
        
        # Update metrics
        if success_rate == 1.0:
            # All checks passed
            metrics.consecutive_failures = 0
            new_status = HealthStatus.HEALTHY
        elif success_rate >= 0.7:
            # Most checks passed
            new_status = HealthStatus.WARNING
            metrics.consecutive_failures += 1
        else:
            # Most checks failed
            new_status = HealthStatus.CRITICAL
            metrics.consecutive_failures += 1
        
        # Update status if changed
        if new_status != metrics.status:
            old_status = metrics.status
            self._update_server_status(server_name, new_status, 
                                     f"Health check results: {passed_checks}/{total_checks} passed")
            
            # Trigger alerts for status changes
            self._trigger_alerts(server_name, old_status, new_status)
    
    def _update_server_status(self, server_name: str, status: HealthStatus, message: str):
        """Update server health status."""
        metrics = self.server_health[server_name]
        old_status = metrics.status
        metrics.status = status
        
        if status == HealthStatus.CRITICAL or status == HealthStatus.DOWN:
            metrics.last_error = message
        else:
            metrics.last_error = None
        
        if old_status != status:
            self.logger.info(f"Server {server_name} status changed: {old_status.value} -> {status.value}")
    
    def _trigger_alerts(self, server_name: str, old_status: HealthStatus, new_status: HealthStatus):
        """Trigger alert callbacks for status changes."""
        message = f"Server {server_name} status changed from {old_status.value} to {new_status.value}"
        
        for callback in self.alert_callbacks:
            try:
                callback(server_name, new_status, message)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    async def _check_connectivity(self, server_name: str) -> bool:
        """Check basic connectivity to server."""
        try:
            # Try to send a simple request
            connection = self.connection_manager.connections.get(server_name)
            if not connection or not connection.is_healthy:
                return False
            
            # Server is connected and healthy
            return True
            
        except Exception as e:
            self.logger.debug(f"Connectivity check failed for {server_name}: {e}")
            return False
    
    async def _check_response_time(self, server_name: str) -> bool:
        """Check server response time."""
        try:
            start_time = time.time()
            
            # Send a lightweight request (ping-like)
            await self.connection_manager.send_request(
                server_name, "ping", {"timestamp": start_time}
            )
            
            response_time = time.time() - start_time
            
            # Update metrics
            metrics = self.server_health[server_name]
            metrics.response_time = response_time
            
            # Consider response times > 5 seconds as unhealthy
            return response_time < 5.0
            
        except Exception as e:
            self.logger.debug(f"Response time check failed for {server_name}: {e}")
            return False
    
    async def _check_capabilities(self, server_name: str) -> bool:
        """Check if server capabilities are still available."""
        try:
            # Get server capabilities
            capabilities = self.connection_manager.get_server_capabilities(server_name)
            
            # If we expected capabilities but got none, that's a problem
            if not capabilities:
                return False
            
            # Capabilities are available
            return True
            
        except Exception as e:
            self.logger.debug(f"Capabilities check failed for {server_name}: {e}")
            return False
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        summary = {
            "monitoring_active": self.monitoring_active,
            "total_servers": len(self.server_health),
            "healthy_servers": 0,
            "warning_servers": 0,
            "critical_servers": 0,
            "down_servers": 0,
            "servers": {}
        }
        
        for server_name, metrics in self.server_health.items():
            status_counts = {
                HealthStatus.HEALTHY: "healthy_servers",
                HealthStatus.WARNING: "warning_servers", 
                HealthStatus.CRITICAL: "critical_servers",
                HealthStatus.DOWN: "down_servers"
            }
            
            count_key = status_counts.get(metrics.status)
            if count_key:
                summary[count_key] += 1
            
            summary["servers"][server_name] = {
                "status": metrics.status.value,
                "response_time": metrics.response_time,
                "success_rate": metrics.success_rate,
                "consecutive_failures": metrics.consecutive_failures,
                "last_check": metrics.last_check.isoformat() if metrics.last_check else None,
                "last_error": metrics.last_error
            }
        
        return summary