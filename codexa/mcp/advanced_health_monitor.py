"""
Advanced health monitoring and recovery system for MCP servers.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics

from .health_monitor import MCPHealthMonitor, HealthStatus, HealthMetrics
from .connection_manager import MCPConnectionManager


class RecoveryAction(Enum):
    """Recovery actions for unhealthy servers."""
    RESTART = "restart"
    RECONNECT = "reconnect"
    DISABLE = "disable"
    ESCALATE = "escalate"
    IGNORE = "ignore"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class HealthAlert:
    """Health monitoring alert."""
    server_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metrics: Optional[HealthMetrics] = None
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "server_name": self.server_name,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "recovery_actions": [action.value for action in self.recovery_actions]
        }


@dataclass
class RecoveryPolicy:
    """Recovery policy configuration."""
    max_restart_attempts: int = 3
    restart_backoff_seconds: int = 30
    max_consecutive_failures: int = 5
    health_check_interval: int = 30
    performance_threshold_cpu: float = 80.0
    performance_threshold_memory: float = 512.0
    response_time_threshold: float = 10.0
    auto_recovery_enabled: bool = True
    escalation_enabled: bool = True
    
    @classmethod
    def conservative(cls) -> "RecoveryPolicy":
        """Conservative recovery policy."""
        return cls(
            max_restart_attempts=2,
            restart_backoff_seconds=60,
            max_consecutive_failures=3,
            auto_recovery_enabled=False
        )
    
    @classmethod
    def aggressive(cls) -> "RecoveryPolicy":
        """Aggressive recovery policy."""
        return cls(
            max_restart_attempts=5,
            restart_backoff_seconds=15,
            max_consecutive_failures=10,
            response_time_threshold=5.0
        )


class AdvancedHealthMonitor(MCPHealthMonitor):
    """Advanced health monitoring with predictive analytics and auto-recovery."""
    
    def __init__(self, connection_manager: MCPConnectionManager,
                 recovery_policy: Optional[RecoveryPolicy] = None):
        super().__init__(connection_manager)
        
        self.recovery_policy = recovery_policy or RecoveryPolicy()
        self.logger = logging.getLogger("advanced_health_monitor")
        
        # Enhanced monitoring data
        self.health_history: Dict[str, List[Tuple[datetime, HealthMetrics]]] = {}
        self.performance_trends: Dict[str, Dict[str, List[float]]] = {}
        self.recovery_attempts: Dict[str, int] = {}
        self.alerts: List[HealthAlert] = []
        self.alert_callbacks: List[Callable[[HealthAlert], None]] = []
        
        # Predictive analytics
        self.prediction_window = timedelta(hours=1)
        self.trend_analysis_points = 10
        
        # Recovery state
        self.recovery_in_progress: Dict[str, bool] = {}
        self.last_recovery_attempt: Dict[str, datetime] = {}
        
    async def start_monitoring(self):
        """Start enhanced monitoring with predictive analytics."""
        await super().start_monitoring()
        
        # Start additional monitoring tasks
        self.prediction_task = asyncio.create_task(self._predictive_monitoring_loop())
        self.recovery_task = asyncio.create_task(self._auto_recovery_loop())
        
        self.logger.info("Advanced health monitoring started")
    
    async def stop_monitoring(self):
        """Stop advanced monitoring."""
        await super().stop_monitoring()
        
        # Stop additional tasks
        if hasattr(self, 'prediction_task'):
            self.prediction_task.cancel()
            try:
                await self.prediction_task
            except asyncio.CancelledError:
                pass
        
        if hasattr(self, 'recovery_task'):
            self.recovery_task.cancel()
            try:
                await self.recovery_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Advanced health monitoring stopped")
    
    async def _check_server_health(self, server_name: str):
        """Enhanced health check with trend analysis."""
        # Run base health check
        await super()._check_server_health(server_name)
        
        # Record health data for trend analysis
        metrics = self.server_health.get(server_name)
        if metrics:
            self._record_health_history(server_name, metrics)
            self._analyze_performance_trends(server_name, metrics)
            
            # Check for alert conditions
            await self._check_alert_conditions(server_name, metrics)
    
    def _record_health_history(self, server_name: str, metrics: HealthMetrics):
        """Record health metrics history."""
        if server_name not in self.health_history:
            self.health_history[server_name] = []
        
        self.health_history[server_name].append((datetime.now(), metrics))
        
        # Keep only recent history (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.health_history[server_name] = [
            (timestamp, m) for timestamp, m in self.health_history[server_name]
            if timestamp > cutoff_time
        ]
    
    def _analyze_performance_trends(self, server_name: str, current_metrics: HealthMetrics):
        """Analyze performance trends for predictive monitoring."""
        if server_name not in self.performance_trends:
            self.performance_trends[server_name] = {
                "response_times": [],
                "success_rates": [],
                "error_rates": []
            }
        
        trends = self.performance_trends[server_name]
        
        # Add current metrics
        trends["response_times"].append(current_metrics.response_time)
        trends["success_rates"].append(current_metrics.success_rate)
        trends["error_rates"].append(current_metrics.error_rate)
        
        # Keep only recent trends
        for metric_type in trends:
            trends[metric_type] = trends[metric_type][-self.trend_analysis_points:]
    
    async def _check_alert_conditions(self, server_name: str, metrics: HealthMetrics):
        """Check for conditions that require alerts."""
        alerts_to_create = []
        
        # Critical health status
        if metrics.status == HealthStatus.CRITICAL:
            alerts_to_create.append(HealthAlert(
                server_name=server_name,
                severity=AlertSeverity.CRITICAL,
                message=f"Server {server_name} is in critical state",
                timestamp=datetime.now(),
                metrics=metrics,
                recovery_actions=[RecoveryAction.RESTART, RecoveryAction.RECONNECT]
            ))
        
        # High response time
        if metrics.response_time > self.recovery_policy.response_time_threshold:
            alerts_to_create.append(HealthAlert(
                server_name=server_name,
                severity=AlertSeverity.WARNING,
                message=f"High response time: {metrics.response_time:.2f}s",
                timestamp=datetime.now(),
                metrics=metrics,
                recovery_actions=[RecoveryAction.RESTART]
            ))
        
        # High error rate
        if metrics.error_rate > 0.3:  # 30% error rate
            alerts_to_create.append(HealthAlert(
                server_name=server_name,
                severity=AlertSeverity.CRITICAL,
                message=f"High error rate: {metrics.error_rate:.1%}",
                timestamp=datetime.now(),
                metrics=metrics,
                recovery_actions=[RecoveryAction.RESTART, RecoveryAction.DISABLE]
            ))
        
        # Consecutive failures threshold
        if metrics.consecutive_failures > self.recovery_policy.max_consecutive_failures:
            alerts_to_create.append(HealthAlert(
                server_name=server_name,
                severity=AlertSeverity.EMERGENCY,
                message=f"Excessive failures: {metrics.consecutive_failures} consecutive",
                timestamp=datetime.now(),
                metrics=metrics,
                recovery_actions=[RecoveryAction.DISABLE, RecoveryAction.ESCALATE]
            ))
        
        # Create alerts and trigger callbacks
        for alert in alerts_to_create:
            await self._create_alert(alert)
    
    async def _create_alert(self, alert: HealthAlert):
        """Create and process a new alert."""
        # Avoid duplicate alerts
        similar_alerts = [
            a for a in self.alerts
            if (a.server_name == alert.server_name and
                a.severity == alert.severity and
                not a.resolved and
                (datetime.now() - a.timestamp) < timedelta(minutes=5))
        ]
        
        if similar_alerts:
            return  # Skip duplicate alert
        
        self.alerts.append(alert)
        
        # Trigger alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback error: {e}")
        
        # Log alert
        self.logger.warning(f"Health alert: {alert.message}")
        
        # Trigger auto-recovery if enabled
        if self.recovery_policy.auto_recovery_enabled:
            await self._trigger_auto_recovery(alert)
    
    async def _predictive_monitoring_loop(self):
        """Predictive monitoring loop to detect potential issues."""
        while self._running:
            try:
                await self._run_predictive_analysis()
                await asyncio.sleep(300)  # Run every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Predictive monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _run_predictive_analysis(self):
        """Run predictive analysis on server health trends."""
        for server_name, trends in self.performance_trends.items():
            try:
                await self._analyze_server_trends(server_name, trends)
            except Exception as e:
                self.logger.error(f"Trend analysis error for {server_name}: {e}")
    
    async def _analyze_server_trends(self, server_name: str, trends: Dict[str, List[float]]):
        """Analyze trends for a specific server."""
        if not trends["response_times"]:
            return
        
        response_times = trends["response_times"]
        
        # Check for deteriorating response times
        if len(response_times) >= 5:
            recent_avg = statistics.mean(response_times[-3:])
            older_avg = statistics.mean(response_times[-6:-3]) if len(response_times) >= 6 else recent_avg
            
            # Significant increase in response time
            if recent_avg > older_avg * 1.5:
                alert = HealthAlert(
                    server_name=server_name,
                    severity=AlertSeverity.WARNING,
                    message=f"Deteriorating performance trend detected",
                    timestamp=datetime.now(),
                    recovery_actions=[RecoveryAction.RESTART]
                )
                await self._create_alert(alert)
        
        # Check success rate trends
        success_rates = trends["success_rates"]
        if len(success_rates) >= 5:
            recent_avg = statistics.mean(success_rates[-3:])
            
            if recent_avg < 0.8:  # Below 80% success rate
                alert = HealthAlert(
                    server_name=server_name,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Low success rate trend: {recent_avg:.1%}",
                    timestamp=datetime.now(),
                    recovery_actions=[RecoveryAction.RESTART, RecoveryAction.RECONNECT]
                )
                await self._create_alert(alert)
    
    async def _auto_recovery_loop(self):
        """Auto-recovery loop for handling unhealthy servers."""
        while self._running:
            try:
                await self._process_recovery_queue()
                await asyncio.sleep(60)  # Process recovery every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Auto-recovery error: {e}")
                await asyncio.sleep(60)
    
    async def _process_recovery_queue(self):
        """Process pending recovery actions."""
        # Find unacknowledged critical alerts
        critical_alerts = [
            alert for alert in self.alerts
            if (alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY] and
                not alert.acknowledged and
                not alert.resolved)
        ]
        
        for alert in critical_alerts:
            if alert.server_name not in self.recovery_in_progress:
                await self._trigger_auto_recovery(alert)
    
    async def _trigger_auto_recovery(self, alert: HealthAlert):
        """Trigger automatic recovery for an alert."""
        server_name = alert.server_name
        
        # Check if recovery is already in progress
        if self.recovery_in_progress.get(server_name, False):
            return
        
        # Check recovery attempt limits
        attempts = self.recovery_attempts.get(server_name, 0)
        if attempts >= self.recovery_policy.max_restart_attempts:
            self.logger.warning(f"Max recovery attempts reached for {server_name}")
            return
        
        # Check backoff period
        last_attempt = self.last_recovery_attempt.get(server_name)
        if last_attempt:
            time_since_last = (datetime.now() - last_attempt).total_seconds()
            if time_since_last < self.recovery_policy.restart_backoff_seconds:
                return  # Still in backoff period
        
        self.recovery_in_progress[server_name] = True
        self.recovery_attempts[server_name] = attempts + 1
        self.last_recovery_attempt[server_name] = datetime.now()
        
        try:
            # Execute recovery actions in order of preference
            for action in alert.recovery_actions:
                if await self._execute_recovery_action(server_name, action):
                    alert.resolved = True
                    break
        finally:
            self.recovery_in_progress[server_name] = False
    
    async def _execute_recovery_action(self, server_name: str, action: RecoveryAction) -> bool:
        """Execute a specific recovery action."""
        self.logger.info(f"Executing recovery action {action.value} for {server_name}")
        
        try:
            if action == RecoveryAction.RESTART:
                return await self._restart_server(server_name)
            elif action == RecoveryAction.RECONNECT:
                return await self._reconnect_server(server_name)
            elif action == RecoveryAction.DISABLE:
                return await self._disable_server(server_name)
            elif action == RecoveryAction.ESCALATE:
                return await self._escalate_issue(server_name)
            
        except Exception as e:
            self.logger.error(f"Recovery action {action.value} failed for {server_name}: {e}")
            return False
        
        return False
    
    async def _restart_server(self, server_name: str) -> bool:
        """Restart a server."""
        try:
            # Disconnect and reconnect
            await self.connection_manager.disconnect_server(server_name)
            await asyncio.sleep(2)  # Brief pause
            success = await self.connection_manager.connect_server(server_name)
            
            if success:
                self.logger.info(f"Successfully restarted server: {server_name}")
                # Reset consecutive failures
                if server_name in self.server_health:
                    self.server_health[server_name].consecutive_failures = 0
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart server {server_name}: {e}")
        
        return False
    
    async def _reconnect_server(self, server_name: str) -> bool:
        """Reconnect to a server."""
        try:
            success = await self.connection_manager.connect_server(server_name)
            if success:
                self.logger.info(f"Successfully reconnected to server: {server_name}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to reconnect to server {server_name}: {e}")
        
        return False
    
    async def _disable_server(self, server_name: str) -> bool:
        """Disable a problematic server."""
        try:
            await self.connection_manager.disconnect_server(server_name)
            
            # Mark server as disabled
            if server_name in self.connection_manager.server_configs:
                self.connection_manager.server_configs[server_name].enabled = False
            
            self.logger.warning(f"Disabled problematic server: {server_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable server {server_name}: {e}")
        
        return False
    
    async def _escalate_issue(self, server_name: str) -> bool:
        """Escalate server issue to administrators."""
        # Create escalation alert
        escalation_alert = HealthAlert(
            server_name=server_name,
            severity=AlertSeverity.EMERGENCY,
            message=f"Server {server_name} requires manual intervention",
            timestamp=datetime.now()
        )
        
        self.alerts.append(escalation_alert)
        
        # Trigger escalation callbacks
        for callback in self.alert_callbacks:
            try:
                callback(escalation_alert)
            except Exception as e:
                self.logger.error(f"Escalation callback error: {e}")
        
        self.logger.critical(f"Escalated server issue: {server_name}")
        return True
    
    def add_alert_callback(self, callback: Callable[[HealthAlert], None]):
        """Add callback for health alerts."""
        self.alert_callbacks.append(callback)
    
    def get_alerts(self, severity: Optional[AlertSeverity] = None,
                  resolved: bool = False) -> List[HealthAlert]:
        """Get health alerts with optional filtering."""
        alerts = [alert for alert in self.alerts if alert.resolved == resolved]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_index: int) -> bool:
        """Acknowledge an alert."""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index].acknowledged = True
            return True
        return False
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total_alerts = len(self.alerts)
        resolved_alerts = len([a for a in self.alerts if a.resolved])
        
        return {
            "total_alerts": total_alerts,
            "resolved_alerts": resolved_alerts,
            "resolution_rate": resolved_alerts / total_alerts if total_alerts > 0 else 0,
            "recovery_attempts": dict(self.recovery_attempts),
            "servers_in_recovery": list(self.recovery_in_progress.keys())
        }
    
    def get_health_trends(self, server_name: str) -> Optional[Dict[str, List[float]]]:
        """Get performance trends for a server."""
        return self.performance_trends.get(server_name)
    
    def export_health_report(self) -> Dict[str, Any]:
        """Export comprehensive health report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self._running,
            "servers": {
                name: {
                    "current_health": metrics.__dict__ if metrics else None,
                    "trends": self.performance_trends.get(name, {}),
                    "recovery_attempts": self.recovery_attempts.get(name, 0),
                    "alerts": [
                        alert.to_dict() for alert in self.alerts
                        if alert.server_name == name
                    ]
                }
                for name, metrics in self.server_health.items()
            },
            "recovery_statistics": self.get_recovery_statistics(),
            "recovery_policy": {
                "max_restart_attempts": self.recovery_policy.max_restart_attempts,
                "auto_recovery_enabled": self.recovery_policy.auto_recovery_enabled,
                "response_time_threshold": self.recovery_policy.response_time_threshold
            }
        }