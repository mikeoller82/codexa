"""
Comprehensive monitoring manager for external system integrations and alerting.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import aiohttp

from rich.console import Console
from rich.panel import Panel


class MonitoringProvider(Enum):
    """Supported monitoring providers."""
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    DATADOG = "datadog"
    NEW_RELIC = "newrelic"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class MetricType(Enum):
    """Types of metrics to monitor."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


@dataclass
class MonitoringConfig:
    """Configuration for monitoring integrations."""
    provider: MonitoringProvider
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    alert_channels: List[str] = field(default_factory=list)
    metric_filters: List[str] = field(default_factory=list)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    retry_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert notification structure."""
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class Metric:
    """Metric data structure."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseMonitoringIntegration:
    """Base class for monitoring integrations."""
    
    def __init__(self, provider: MonitoringProvider, config: MonitoringConfig):
        self.provider = provider
        self.config = config
        self.logger = logging.getLogger(f"codexa.monitoring.{provider.value}")
        self.is_connected = False
        
        # Rate limiting
        self.last_requests: Dict[str, datetime] = {}
        
        # Retry configuration
        self.max_retries = config.retry_config.get('max_retries', 3)
        self.retry_delay = config.retry_config.get('retry_delay', 1.0)
    
    async def connect(self) -> bool:
        """Connect to the monitoring service."""
        raise NotImplementedError
    
    async def disconnect(self):
        """Disconnect from the monitoring service."""
        self.is_connected = False
    
    async def send_metric(self, metric: Metric) -> bool:
        """Send a metric to the monitoring service."""
        raise NotImplementedError
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert to the monitoring service."""
        raise NotImplementedError
    
    def _check_rate_limit(self, operation: str) -> bool:
        """Check if operation is rate limited."""
        if operation not in self.config.rate_limits:
            return True
        
        limit = self.config.rate_limits[operation]
        if limit <= 0:
            return True
        
        now = datetime.now()
        if operation in self.last_requests:
            time_since_last = (now - self.last_requests[operation]).total_seconds()
            if time_since_last < (60.0 / limit):  # Convert per-minute limit to seconds
                return False
        
        self.last_requests[operation] = now
        return True
    
    async def _retry_operation(self, operation: Callable, *args, **kwargs):
        """Retry an operation with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                
                wait_time = self.retry_delay * (2 ** attempt)
                self.logger.warning(f"Operation failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)


class PrometheusIntegration(BaseMonitoringIntegration):
    """Prometheus monitoring integration."""
    
    def __init__(self, config: MonitoringConfig):
        super().__init__(MonitoringProvider.PROMETHEUS, config)
        self.metrics_endpoint = config.config.get('metrics_endpoint', 'http://localhost:9090')
        self.push_gateway = config.config.get('push_gateway', 'http://localhost:9091')
        self.job_name = config.config.get('job_name', 'codexa')
        
        # Metric registry
        self.registered_metrics: Dict[str, Metric] = {}
    
    async def connect(self) -> bool:
        """Connect to Prometheus."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.metrics_endpoint}/api/v1/query?query=up") as response:
                    if response.status == 200:
                        self.is_connected = True
                        self.logger.info("Connected to Prometheus")
                        return True
                    else:
                        self.logger.error(f"Failed to connect to Prometheus: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"Prometheus connection failed: {e}")
            return False
    
    async def send_metric(self, metric: Metric) -> bool:
        """Send metric to Prometheus via push gateway."""
        if not self._check_rate_limit('send_metric'):
            self.logger.debug(f"Rate limit exceeded for metric: {metric.name}")
            return False
        
        try:
            # Format metric for Prometheus
            prometheus_metric = self._format_prometheus_metric(metric)
            
            # Send to push gateway
            url = f"{self.push_gateway}/metrics/job/{self.job_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=prometheus_metric) as response:
                    if response.status in [200, 202]:
                        self.registered_metrics[metric.name] = metric
                        return True
                    else:
                        self.logger.error(f"Failed to send metric to Prometheus: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error sending metric to Prometheus: {e}")
            return False
    
    def _format_prometheus_metric(self, metric: Metric) -> str:
        """Format metric in Prometheus exposition format."""
        lines = []
        
        # Add help text
        lines.append(f"# HELP {metric.name} {metric.metadata.get('description', 'Codexa metric')}")
        
        # Add type
        prom_type = {
            MetricType.COUNTER: "counter",
            MetricType.GAUGE: "gauge",
            MetricType.HISTOGRAM: "histogram",
            MetricType.SUMMARY: "summary",
            MetricType.TIMER: "histogram"
        }.get(metric.metric_type, "gauge")
        
        lines.append(f"# TYPE {metric.name} {prom_type}")
        
        # Format tags
        tag_str = ""
        if metric.tags:
            tag_pairs = [f'{key}="{value}"' for key, value in metric.tags.items()]
            tag_str = "{" + ",".join(tag_pairs) + "}"
        
        # Add metric value
        lines.append(f"{metric.name}{tag_str} {metric.value} {int(metric.timestamp.timestamp() * 1000)}")
        
        return "\n".join(lines)
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Prometheus Alertmanager."""
        if not self._check_rate_limit('send_alert'):
            return False
        
        alertmanager_url = self.config.config.get('alertmanager_url')
        if not alertmanager_url:
            self.logger.warning("No Alertmanager URL configured")
            return False
        
        try:
            alert_payload = {
                "alerts": [{
                    "labels": {
                        "alertname": alert.title,
                        "severity": alert.severity.value,
                        "source": alert.source,
                        "instance": self.job_name
                    },
                    "annotations": {
                        "description": alert.message,
                        "timestamp": alert.timestamp.isoformat()
                    },
                    "startsAt": alert.timestamp.isoformat(),
                    "generatorURL": f"http://localhost/codexa/alert/{alert.title}"
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{alertmanager_url}/api/v1/alerts",
                    json=alert_payload
                ) as response:
                    return response.status in [200, 201, 202]
                    
        except Exception as e:
            self.logger.error(f"Error sending alert to Alertmanager: {e}")
            return False


class SlackIntegration(BaseMonitoringIntegration):
    """Slack alerting integration."""
    
    def __init__(self, config: MonitoringConfig):
        super().__init__(MonitoringProvider.SLACK, config)
        self.webhook_url = config.config.get('webhook_url')
        self.channel = config.config.get('channel', '#alerts')
        self.username = config.config.get('username', 'Codexa')
        self.icon_emoji = config.config.get('icon_emoji', ':robot_face:')
    
    async def connect(self) -> bool:
        """Test Slack connection."""
        if not self.webhook_url:
            self.logger.error("No Slack webhook URL configured")
            return False
        
        try:
            test_payload = {
                "text": "Codexa monitoring connection test",
                "channel": self.channel,
                "username": self.username,
                "icon_emoji": self.icon_emoji
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=test_payload) as response:
                    if response.status == 200:
                        self.is_connected = True
                        self.logger.info("Connected to Slack")
                        return True
                    else:
                        self.logger.error(f"Slack connection failed: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Slack connection error: {e}")
            return False
    
    async def send_metric(self, metric: Metric) -> bool:
        """Metrics are not typically sent to Slack."""
        return True
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack channel."""
        if not self.webhook_url or not self._check_rate_limit('send_alert'):
            return False
        
        try:
            # Format alert for Slack
            color = self._get_alert_color(alert.severity)
            
            payload = {
                "channel": self.channel,
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "attachments": [{
                    "color": color,
                    "title": f"🚨 {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Source",
                            "value": alert.source,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True
                        }
                    ],
                    "footer": "Codexa Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }
            
            # Add metadata fields
            for key, value in alert.metadata.items():
                if len(payload["attachments"][0]["fields"]) < 10:  # Slack limit
                    payload["attachments"][0]["fields"].append({
                        "title": key.replace("_", " ").title(),
                        "value": str(value),
                        "short": True
                    })
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.error(f"Error sending alert to Slack: {e}")
            return False
    
    def _get_alert_color(self, severity: AlertSeverity) -> str:
        """Get Slack color for alert severity."""
        colors = {
            AlertSeverity.LOW: "#36a64f",       # Green
            AlertSeverity.MEDIUM: "#ff9900",    # Orange
            AlertSeverity.HIGH: "#ff0000",      # Red
            AlertSeverity.CRITICAL: "#8B0000",  # Dark Red
            AlertSeverity.EMERGENCY: "#4B0082"  # Purple
        }
        return colors.get(severity, "#36a64f")


class WebhookIntegration(BaseMonitoringIntegration):
    """Generic webhook integration."""
    
    def __init__(self, config: MonitoringConfig):
        super().__init__(MonitoringProvider.WEBHOOK, config)
        self.webhook_urls = config.config.get('webhook_urls', [])
        self.headers = config.config.get('headers', {})
        self.auth_token = config.config.get('auth_token')
        
        if self.auth_token:
            self.headers['Authorization'] = f'Bearer {self.auth_token}'
    
    async def connect(self) -> bool:
        """Test webhook endpoints."""
        if not self.webhook_urls:
            self.logger.error("No webhook URLs configured")
            return False
        
        successful_connections = 0
        
        for url in self.webhook_urls:
            try:
                test_payload = {
                    "type": "connection_test",
                    "timestamp": datetime.now().isoformat(),
                    "source": "codexa"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=test_payload, headers=self.headers) as response:
                        if response.status in [200, 201, 202, 204]:
                            successful_connections += 1
                        else:
                            self.logger.warning(f"Webhook test failed for {url}: {response.status}")
                            
            except Exception as e:
                self.logger.warning(f"Webhook connection test failed for {url}: {e}")
        
        self.is_connected = successful_connections > 0
        if self.is_connected:
            self.logger.info(f"Connected to {successful_connections}/{len(self.webhook_urls)} webhooks")
        
        return self.is_connected
    
    async def send_metric(self, metric: Metric) -> bool:
        """Send metric via webhook."""
        if not self._check_rate_limit('send_metric'):
            return False
        
        payload = {
            "type": "metric",
            "timestamp": datetime.now().isoformat(),
            "metric": {
                "name": metric.name,
                "value": metric.value,
                "type": metric.metric_type.value,
                "timestamp": metric.timestamp.isoformat(),
                "tags": metric.tags,
                "metadata": metric.metadata
            }
        }
        
        return await self._send_to_webhooks(payload)
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        if not self._check_rate_limit('send_alert'):
            return False
        
        payload = {
            "type": "alert",
            "timestamp": datetime.now().isoformat(),
            "alert": {
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata,
                "resolved": alert.resolved,
                "resolution_time": alert.resolution_time.isoformat() if alert.resolution_time else None
            }
        }
        
        return await self._send_to_webhooks(payload)
    
    async def _send_to_webhooks(self, payload: Dict[str, Any]) -> bool:
        """Send payload to all configured webhooks."""
        successful_sends = 0
        
        tasks = []
        for url in self.webhook_urls:
            task = self._send_to_single_webhook(url, payload)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result is True:
                successful_sends += 1
            elif isinstance(result, Exception):
                self.logger.error(f"Webhook send error: {result}")
        
        return successful_sends > 0
    
    async def _send_to_single_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send payload to a single webhook."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return response.status in [200, 201, 202, 204]
        except Exception as e:
            self.logger.error(f"Error sending to webhook {url}: {e}")
            return False


class MonitoringManager:
    """Main monitoring manager that coordinates all integrations."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.monitoring")
        
        # Integration management
        self.integrations: Dict[MonitoringProvider, BaseMonitoringIntegration] = {}
        self.active_integrations: Set[MonitoringProvider] = set()
        
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_rules: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.monitoring_stats = {
            'metrics_sent': 0,
            'alerts_sent': 0,
            'integration_errors': 0,
            'last_heartbeat': None
        }
        
        # Background tasks
        self.heartbeat_task = None
        self.alert_cleanup_task = None
    
    def add_integration(self, integration: BaseMonitoringIntegration):
        """Add a monitoring integration."""
        self.integrations[integration.provider] = integration
        self.logger.info(f"Added monitoring integration: {integration.provider.value}")
    
    async def connect_all(self) -> Dict[MonitoringProvider, bool]:
        """Connect to all configured integrations."""
        results = {}
        
        for provider, integration in self.integrations.items():
            if not integration.config.enabled:
                self.logger.info(f"Skipping disabled integration: {provider.value}")
                results[provider] = False
                continue
            
            try:
                connected = await integration.connect()
                results[provider] = connected
                
                if connected:
                    self.active_integrations.add(provider)
                    self.logger.info(f"Successfully connected to {provider.value}")
                else:
                    self.logger.warning(f"Failed to connect to {provider.value}")
                    
            except Exception as e:
                self.logger.error(f"Error connecting to {provider.value}: {e}")
                results[provider] = False
        
        # Start background tasks if we have active integrations
        if self.active_integrations:
            await self._start_background_tasks()
        
        return results
    
    async def send_metric(self, metric: Metric, providers: Optional[List[MonitoringProvider]] = None) -> Dict[MonitoringProvider, bool]:
        """Send metric to specified providers or all active providers."""
        if providers is None:
            providers = list(self.active_integrations)
        
        results = {}
        
        for provider in providers:
            if provider not in self.active_integrations:
                results[provider] = False
                continue
            
            integration = self.integrations[provider]
            
            try:
                success = await integration.send_metric(metric)
                results[provider] = success
                
                if success:
                    self.monitoring_stats['metrics_sent'] += 1
                else:
                    self.monitoring_stats['integration_errors'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error sending metric to {provider.value}: {e}")
                results[provider] = False
                self.monitoring_stats['integration_errors'] += 1
        
        return results
    
    async def send_alert(self, alert: Alert, providers: Optional[List[MonitoringProvider]] = None) -> Dict[MonitoringProvider, bool]:
        """Send alert to specified providers or all active providers."""
        if providers is None:
            providers = list(self.active_integrations)
        
        # Store alert
        alert_key = f"{alert.source}:{alert.title}"
        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)
        
        # Keep alert history manageable
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        results = {}
        
        for provider in providers:
            if provider not in self.active_integrations:
                results[provider] = False
                continue
            
            integration = self.integrations[provider]
            
            try:
                success = await integration.send_alert(alert)
                results[provider] = success
                
                if success:
                    self.monitoring_stats['alerts_sent'] += 1
                else:
                    self.monitoring_stats['integration_errors'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error sending alert to {provider.value}: {e}")
                results[provider] = False
                self.monitoring_stats['integration_errors'] += 1
        
        return results
    
    async def resolve_alert(self, alert_key: str) -> bool:
        """Mark an alert as resolved."""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.resolved = True
            alert.resolution_time = datetime.now()
            
            del self.active_alerts[alert_key]
            
            self.logger.info(f"Alert resolved: {alert_key}")
            return True
        
        return False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        return {
            'active_integrations': [p.value for p in self.active_integrations],
            'integration_status': {
                provider.value: {
                    'connected': integration.is_connected,
                    'enabled': integration.config.enabled
                }
                for provider, integration in self.integrations.items()
            },
            'active_alerts': len(self.active_alerts),
            'total_alerts_history': len(self.alert_history),
            'monitoring_stats': self.monitoring_stats,
            'alert_rules': len(self.alert_rules)
        }
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks."""
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        if not self.alert_cleanup_task:
            self.alert_cleanup_task = asyncio.create_task(self._alert_cleanup_loop())
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to monitoring systems."""
        while self.active_integrations:
            try:
                heartbeat_metric = Metric(
                    name="codexa_heartbeat",
                    value=1.0,
                    metric_type=MetricType.GAUGE,
                    tags={"source": "codexa", "type": "heartbeat"}
                )
                
                await self.send_metric(heartbeat_metric)
                self.monitoring_stats['last_heartbeat'] = datetime.now()
                
                await asyncio.sleep(60)  # Heartbeat every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(60)
    
    async def _alert_cleanup_loop(self):
        """Clean up old resolved alerts."""
        while True:
            try:
                # Clean up alerts older than 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                # Clean alert history
                self.alert_history = [
                    alert for alert in self.alert_history
                    if alert.timestamp > cutoff_time
                ]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Alert cleanup error: {e}")
                await asyncio.sleep(3600)
    
    async def shutdown(self):
        """Shutdown monitoring manager and all integrations."""
        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.alert_cleanup_task:
            self.alert_cleanup_task.cancel()
        
        # Disconnect all integrations
        for integration in self.integrations.values():
            try:
                await integration.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting {integration.provider.value}: {e}")
        
        self.active_integrations.clear()
        self.logger.info("Monitoring manager shutdown complete")