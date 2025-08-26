"""
Advanced analytics dashboard system for comprehensive Codexa monitoring and insights.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.chart import Chart
from rich.align import Align


class MetricType(Enum):
    """Types of metrics tracked in the dashboard."""
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate" 
    USER_ACTIVITY = "user_activity"
    RESOURCE_USAGE = "resource_usage"
    SUCCESS_RATE = "success_rate"
    RESPONSE_TIME = "response_time"
    PROVIDER_HEALTH = "provider_health"
    MCP_STATUS = "mcp_status"
    COMMAND_USAGE = "command_usage"
    PREDICTION_ACCURACY = "prediction_accuracy"


class WidgetType(Enum):
    """Types of dashboard widgets."""
    METRIC_CARD = "metric_card"
    TIME_SERIES = "time_series"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    GAUGE = "gauge"
    TABLE = "table"
    LOG_STREAM = "log_stream"
    ALERT_PANEL = "alert_panel"
    HEATMAP = "heatmap"
    SPARKLINE = "sparkline"


@dataclass
class MetricValue:
    """Represents a metric value with metadata."""
    value: Union[int, float, str]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class MetricWidget:
    """Configuration for a dashboard widget."""
    widget_id: str
    widget_type: WidgetType
    metric_type: MetricType
    title: str
    description: str = ""
    refresh_interval: float = 5.0  # seconds
    size: Tuple[int, int] = (30, 10)  # width, height
    config: Dict[str, Any] = field(default_factory=dict)
    data_source: Optional[Callable] = None


@dataclass
class DashboardConfig:
    """Dashboard configuration and layout."""
    title: str = "Codexa Analytics Dashboard"
    refresh_interval: float = 2.0  # seconds
    auto_refresh: bool = True
    widgets: List[MetricWidget] = field(default_factory=list)
    layout_grid: Tuple[int, int] = (3, 3)  # columns, rows
    theme: str = "default"
    export_enabled: bool = True
    alerts_enabled: bool = True


class AnalyticsDashboard:
    """Advanced analytics dashboard with real-time monitoring and insights."""
    
    def __init__(self, config: DashboardConfig, console: Optional[Console] = None):
        self.config = config
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.analytics.dashboard")
        
        # Data storage
        self.metrics_store: Dict[str, List[MetricValue]] = {}
        self.widget_cache: Dict[str, Any] = {}
        self.alerts: List[Dict[str, Any]] = []
        
        # State management
        self.is_running = False
        self.last_refresh = None
        self.refresh_task = None
        
        # Performance tracking
        self.render_times: List[float] = []
        self.data_fetch_times: List[float] = []
        
        # Initialize built-in widgets
        self._initialize_default_widgets()
    
    async def start(self, duration: Optional[float] = None):
        """Start the dashboard with optional duration limit."""
        self.is_running = True
        self.logger.info("Starting analytics dashboard")
        
        # Create layout
        layout = self._create_layout()
        
        # Start live display
        with Live(layout, console=self.console, refresh_per_second=1/self.config.refresh_interval) as live:
            self.live_display = live
            
            try:
                start_time = datetime.now()
                while self.is_running:
                    # Check duration limit
                    if duration and (datetime.now() - start_time).total_seconds() >= duration:
                        break
                    
                    # Refresh dashboard data
                    await self._refresh_data()
                    
                    # Update layout
                    updated_layout = self._create_layout()
                    live.update(updated_layout)
                    
                    # Wait for next refresh
                    await asyncio.sleep(self.config.refresh_interval)
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Dashboard stopped by user[/yellow]")
            finally:
                self.is_running = False
                self.logger.info("Analytics dashboard stopped")
    
    def stop(self):
        """Stop the dashboard."""
        self.is_running = False
    
    def add_metric(self, metric_type: MetricType, value: MetricValue):
        """Add a metric value to the dashboard."""
        metric_key = metric_type.value
        
        if metric_key not in self.metrics_store:
            self.metrics_store[metric_key] = []
        
        self.metrics_store[metric_key].append(value)
        
        # Keep only recent metrics (last 1000 entries)
        if len(self.metrics_store[metric_key]) > 1000:
            self.metrics_store[metric_key] = self.metrics_store[metric_key][-1000:]
    
    def add_widget(self, widget: MetricWidget):
        """Add a custom widget to the dashboard."""
        self.config.widgets.append(widget)
        self.logger.info(f"Added widget: {widget.title}")
    
    def _create_layout(self) -> Layout:
        """Create the dashboard layout with all widgets."""
        start_time = datetime.now()
        
        # Main layout
        layout = Layout(name="dashboard")
        
        # Header
        header = self._create_header()
        
        # Grid of widgets
        widgets_grid = self._create_widgets_grid()
        
        # Footer with status
        footer = self._create_footer()
        
        # Combine layouts
        layout.split_column(
            Layout(header, name="header", size=3),
            Layout(widgets_grid, name="widgets", ratio=1),
            Layout(footer, name="footer", size=3)
        )
        
        # Track render performance
        render_time = (datetime.now() - start_time).total_seconds()
        self.render_times.append(render_time)
        if len(self.render_times) > 100:
            self.render_times = self.render_times[-100:]
        
        return layout
    
    def _create_header(self) -> Panel:
        """Create dashboard header with title and status."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uptime = self._get_uptime()
        
        header_content = Text()
        header_content.append(f"🚀 {self.config.title}", style="bold cyan")
        header_content.append(f" | {current_time}", style="dim")
        header_content.append(f" | Uptime: {uptime}", style="green")
        
        if self.alerts:
            alert_count = len([a for a in self.alerts if a.get("level") == "critical"])
            if alert_count > 0:
                header_content.append(f" | 🚨 {alert_count} Critical Alerts", style="bold red")
        
        return Panel(
            Align.center(header_content),
            style="blue",
            padding=(0, 1)
        )
    
    def _create_widgets_grid(self) -> Layout:
        """Create grid layout for widgets."""
        if not self.config.widgets:
            return Panel("No widgets configured", style="dim")
        
        # Create grid based on configuration
        cols, rows = self.config.layout_grid
        
        # Create widget panels
        widget_panels = []
        for i, widget in enumerate(self.config.widgets[:cols * rows]):
            panel = self._create_widget_panel(widget)
            widget_panels.append(panel)
        
        # Fill remaining slots with empty panels
        while len(widget_panels) < cols * rows:
            widget_panels.append(Panel("", style="dim"))
        
        # Create layout grid
        layout = Layout()
        
        # Split into rows
        row_layouts = []
        for row in range(rows):
            row_layout = Layout()
            
            # Split row into columns
            col_panels = widget_panels[row * cols:(row + 1) * cols]
            if len(col_panels) == 1:
                row_layout.update(col_panels[0])
            else:
                row_layout.split_row(*[Layout(panel) for panel in col_panels])
            
            row_layouts.append(row_layout)
        
        if len(row_layouts) == 1:
            layout.update(row_layouts[0])
        else:
            layout.split_column(*row_layouts)
        
        return layout
    
    def _create_widget_panel(self, widget: MetricWidget) -> Panel:
        """Create a panel for a specific widget."""
        try:
            # Get widget data
            widget_data = self._get_widget_data(widget)
            
            # Create widget content based on type
            if widget.widget_type == WidgetType.METRIC_CARD:
                content = self._create_metric_card(widget, widget_data)
            elif widget.widget_type == WidgetType.TIME_SERIES:
                content = self._create_time_series(widget, widget_data)
            elif widget.widget_type == WidgetType.TABLE:
                content = self._create_table(widget, widget_data)
            elif widget.widget_type == WidgetType.GAUGE:
                content = self._create_gauge(widget, widget_data)
            elif widget.widget_type == WidgetType.ALERT_PANEL:
                content = self._create_alert_panel(widget, widget_data)
            else:
                content = f"Widget type {widget.widget_type.value} not implemented"
            
            return Panel(
                content,
                title=widget.title,
                border_style="blue" if not self._has_widget_alerts(widget) else "red"
            )
            
        except Exception as e:
            self.logger.error(f"Error creating widget {widget.title}: {e}")
            return Panel(
                f"Error: {str(e)}",
                title=widget.title,
                border_style="red"
            )
    
    def _get_widget_data(self, widget: MetricWidget) -> Any:
        """Get data for a specific widget."""
        # Check cache first
        cache_key = f"{widget.widget_id}_{widget.metric_type.value}"
        
        # Use custom data source if available
        if widget.data_source:
            try:
                return widget.data_source()
            except Exception as e:
                self.logger.error(f"Custom data source failed for {widget.title}: {e}")
                return None
        
        # Get data from metrics store
        metric_key = widget.metric_type.value
        if metric_key in self.metrics_store:
            return self.metrics_store[metric_key]
        
        return []
    
    def _create_metric_card(self, widget: MetricWidget, data: List[MetricValue]) -> str:
        """Create a metric card display."""
        if not data:
            return "No data available"
        
        latest = data[-1]
        
        # Calculate trend if enough data points
        trend_indicator = ""
        if len(data) >= 2:
            current_val = float(latest.value) if isinstance(latest.value, (int, float)) else 0
            previous_val = float(data[-2].value) if isinstance(data[-2].value, (int, float)) else 0
            
            if current_val > previous_val:
                trend_indicator = " 📈"
            elif current_val < previous_val:
                trend_indicator = " 📉"
            else:
                trend_indicator = " ➡️"
        
        # Format value
        if isinstance(latest.value, float):
            formatted_value = f"{latest.value:.2f}"
        else:
            formatted_value = str(latest.value)
        
        content = []
        content.append(f"[bold green]{formatted_value}[/bold green]{trend_indicator}")
        content.append(f"[dim]Last updated: {latest.timestamp.strftime('%H:%M:%S')}[/dim]")
        
        if widget.description:
            content.append(f"[dim]{widget.description}[/dim]")
        
        return "\n".join(content)
    
    def _create_time_series(self, widget: MetricWidget, data: List[MetricValue]) -> str:
        """Create a time series chart (simplified ASCII representation)."""
        if not data or len(data) < 2:
            return "Insufficient data for chart"
        
        # Get last 20 data points
        recent_data = data[-20:]
        values = [float(d.value) if isinstance(d.value, (int, float)) else 0 for d in recent_data]
        
        if not values or all(v == 0 for v in values):
            return "No numeric data available"
        
        # Create simple ASCII sparkline
        min_val = min(values)
        max_val = max(values)
        
        if min_val == max_val:
            return f"Constant value: {min_val}"
        
        # Normalize to 0-7 range for bar heights
        normalized = [(v - min_val) / (max_val - min_val) * 7 for v in values]
        
        # Create sparkline
        bars = []
        for val in normalized:
            height = int(val)
            if height == 0:
                bars.append('▁')
            elif height == 1:
                bars.append('▂')
            elif height == 2:
                bars.append('▃')
            elif height == 3:
                bars.append('▄')
            elif height == 4:
                bars.append('▅')
            elif height == 5:
                bars.append('▆')
            elif height == 6:
                bars.append('▇')
            else:
                bars.append('█')
        
        sparkline = ''.join(bars)
        
        content = []
        content.append(f"Range: {min_val:.2f} - {max_val:.2f}")
        content.append(f"Current: {values[-1]:.2f}")
        content.append(f"{sparkline}")
        
        return "\n".join(content)
    
    def _create_table(self, widget: MetricWidget, data: List[MetricValue]) -> Table:
        """Create a data table."""
        table = Table(show_header=True, header_style="bold blue")
        
        if widget.metric_type == MetricType.COMMAND_USAGE:
            table.add_column("Command", style="cyan")
            table.add_column("Count", justify="right", style="green")
            table.add_column("Last Used", style="dim")
            
            # Aggregate command usage data
            command_stats = {}
            for metric in data[-50:]:  # Last 50 entries
                if isinstance(metric.value, dict):
                    command = metric.value.get('command', 'unknown')
                    if command not in command_stats:
                        command_stats[command] = {'count': 0, 'last_used': metric.timestamp}
                    command_stats[command]['count'] += 1
                    if metric.timestamp > command_stats[command]['last_used']:
                        command_stats[command]['last_used'] = metric.timestamp
            
            # Sort by usage count
            sorted_commands = sorted(command_stats.items(), key=lambda x: x[1]['count'], reverse=True)
            
            for command, stats in sorted_commands[:10]:  # Top 10
                table.add_row(
                    command,
                    str(stats['count']),
                    stats['last_used'].strftime('%H:%M:%S')
                )
        
        else:
            # Generic table for other metrics
            table.add_column("Value", style="green")
            table.add_column("Time", style="dim")
            
            for metric in data[-10:]:  # Last 10 entries
                table.add_row(
                    str(metric.value),
                    metric.timestamp.strftime('%H:%M:%S')
                )
        
        return table
    
    def _create_gauge(self, widget: MetricWidget, data: List[MetricValue]) -> str:
        """Create a gauge display."""
        if not data:
            return "No data"
        
        latest = data[-1]
        if not isinstance(latest.value, (int, float)):
            return "Non-numeric data"
        
        value = float(latest.value)
        max_val = widget.config.get('max_value', 100)
        min_val = widget.config.get('min_value', 0)
        
        # Normalize to 0-1
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))  # Clamp
        
        # Create gauge bar
        bar_length = 20
        filled = int(normalized * bar_length)
        empty = bar_length - filled
        
        # Color based on thresholds
        if normalized < 0.3:
            color = "green"
        elif normalized < 0.7:
            color = "yellow"
        else:
            color = "red"
        
        gauge_bar = f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
        percentage = f"{normalized * 100:.1f}%"
        
        return f"{gauge_bar}\n{value:.2f} / {max_val} ({percentage})"
    
    def _create_alert_panel(self, widget: MetricWidget, data: Any) -> str:
        """Create alerts panel display."""
        if not self.alerts:
            return "[green]All systems operational[/green]"
        
        content = []
        critical_alerts = [a for a in self.alerts if a.get('level') == 'critical']
        warning_alerts = [a for a in self.alerts if a.get('level') == 'warning']
        
        if critical_alerts:
            content.append(f"[red]🚨 {len(critical_alerts)} Critical Alerts[/red]")
            for alert in critical_alerts[:3]:  # Show top 3
                content.append(f"[red]• {alert.get('message', 'Unknown alert')}[/red]")
        
        if warning_alerts:
            content.append(f"[yellow]⚠️ {len(warning_alerts)} Warnings[/yellow]")
            for alert in warning_alerts[:2]:  # Show top 2
                content.append(f"[yellow]• {alert.get('message', 'Unknown warning')}[/yellow]")
        
        return "\n".join(content)
    
    def _create_footer(self) -> Panel:
        """Create dashboard footer with performance stats."""
        footer_content = []
        
        # Performance stats
        if self.render_times:
            avg_render = statistics.mean(self.render_times[-10:]) * 1000  # ms
            footer_content.append(f"Render: {avg_render:.1f}ms")
        
        if self.data_fetch_times:
            avg_fetch = statistics.mean(self.data_fetch_times[-10:]) * 1000  # ms
            footer_content.append(f"Fetch: {avg_fetch:.1f}ms")
        
        # Memory usage (simplified)
        widget_count = len(self.config.widgets)
        metric_count = sum(len(metrics) for metrics in self.metrics_store.values())
        footer_content.append(f"Widgets: {widget_count}")
        footer_content.append(f"Metrics: {metric_count}")
        
        footer_text = " | ".join(footer_content)
        
        return Panel(
            Align.center(Text(footer_text, style="dim")),
            style="blue",
            padding=(0, 1)
        )
    
    async def _refresh_data(self):
        """Refresh dashboard data from sources."""
        start_time = datetime.now()
        
        try:
            # Update last refresh timestamp
            self.last_refresh = datetime.now()
            
            # Clear old alerts
            cutoff_time = datetime.now() - timedelta(minutes=5)
            self.alerts = [a for a in self.alerts if a.get('timestamp', datetime.min) > cutoff_time]
            
            # Refresh widget data (this would call external data sources)
            for widget in self.config.widgets:
                if widget.data_source:
                    try:
                        # Refresh custom data sources
                        widget_data = widget.data_source()
                        # Cache the data
                        cache_key = f"{widget.widget_id}_{widget.metric_type.value}"
                        self.widget_cache[cache_key] = widget_data
                    except Exception as e:
                        self.logger.error(f"Failed to refresh widget {widget.title}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error refreshing dashboard data: {e}")
        
        # Track fetch performance
        fetch_time = (datetime.now() - start_time).total_seconds()
        self.data_fetch_times.append(fetch_time)
        if len(self.data_fetch_times) > 100:
            self.data_fetch_times = self.data_fetch_times[-100:]
    
    def _has_widget_alerts(self, widget: MetricWidget) -> bool:
        """Check if widget has any alerts."""
        return any(
            alert.get('widget_id') == widget.widget_id 
            for alert in self.alerts 
            if alert.get('level') == 'critical'
        )
    
    def _get_uptime(self) -> str:
        """Get formatted uptime string."""
        if not hasattr(self, '_start_time'):
            self._start_time = datetime.now()
        
        uptime = datetime.now() - self._start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        
        return f"{hours:02d}:{minutes:02d}"
    
    def add_alert(self, level: str, message: str, widget_id: Optional[str] = None):
        """Add an alert to the dashboard."""
        alert = {
            'level': level,
            'message': message,
            'timestamp': datetime.now(),
            'widget_id': widget_id
        }
        
        self.alerts.append(alert)
        self.logger.warning(f"Dashboard alert ({level}): {message}")
    
    def export_metrics(self, format: str = "json", filename: Optional[str] = None) -> str:
        """Export metrics data."""
        if not self.config.export_enabled:
            raise ValueError("Export is disabled")
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'dashboard_config': {
                'title': self.config.title,
                'widgets': [
                    {
                        'id': w.widget_id,
                        'type': w.widget_type.value,
                        'metric_type': w.metric_type.value,
                        'title': w.title
                    }
                    for w in self.config.widgets
                ]
            },
            'metrics': {}
        }
        
        # Export metrics data
        for metric_type, values in self.metrics_store.items():
            export_data['metrics'][metric_type] = [
                {
                    'value': v.value,
                    'timestamp': v.timestamp.isoformat(),
                    'metadata': v.metadata,
                    'tags': v.tags
                }
                for v in values[-100:]  # Last 100 values
            ]
        
        if format.lower() == "json":
            result = json.dumps(export_data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        # Save to file if filename provided
        if filename:
            with open(filename, 'w') as f:
                f.write(result)
            self.logger.info(f"Metrics exported to {filename}")
        
        return result
    
    def _initialize_default_widgets(self):
        """Initialize default dashboard widgets."""
        # Performance widget
        self.config.widgets.append(MetricWidget(
            widget_id="performance",
            widget_type=WidgetType.METRIC_CARD,
            metric_type=MetricType.PERFORMANCE,
            title="System Performance",
            description="Overall system performance score"
        ))
        
        # Error rate widget
        self.config.widgets.append(MetricWidget(
            widget_id="error_rate",
            widget_type=WidgetType.GAUGE,
            metric_type=MetricType.ERROR_RATE,
            title="Error Rate",
            description="Percentage of failed operations",
            config={"max_value": 100, "min_value": 0}
        ))
        
        # Response time trend
        self.config.widgets.append(MetricWidget(
            widget_id="response_time",
            widget_type=WidgetType.TIME_SERIES,
            metric_type=MetricType.RESPONSE_TIME,
            title="Response Time Trend",
            description="API response time over time"
        ))
        
        # Command usage table
        self.config.widgets.append(MetricWidget(
            widget_id="command_usage",
            widget_type=WidgetType.TABLE,
            metric_type=MetricType.COMMAND_USAGE,
            title="Command Usage",
            description="Most frequently used commands"
        ))
        
        # Alerts panel
        self.config.widgets.append(MetricWidget(
            widget_id="alerts",
            widget_type=WidgetType.ALERT_PANEL,
            metric_type=MetricType.USER_ACTIVITY,  # Not used for alerts
            title="System Alerts",
            description="Critical alerts and warnings"
        ))
        
        # MCP status
        self.config.widgets.append(MetricWidget(
            widget_id="mcp_status",
            widget_type=WidgetType.METRIC_CARD,
            metric_type=MetricType.MCP_STATUS,
            title="MCP Servers",
            description="Active MCP server count"
        ))