"""
Tool Performance Monitor - Advanced analytics and monitoring for the Codexa tool system.
"""

import time
import asyncio
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import logging
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

from .tool_interface import Tool, ToolResult, ToolStatus


@dataclass
class ToolExecutionMetrics:
    """Metrics for a single tool execution."""
    
    tool_name: str
    execution_id: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: ToolStatus = ToolStatus.PENDING
    success: bool = False
    confidence_score: float = 0.0
    error_message: Optional[str] = None
    memory_usage: Optional[float] = None  # MB
    cpu_usage: Optional[float] = None     # %
    
    # Request context
    request_text: str = ""
    context_size: int = 0
    
    # Result metrics
    result_size: int = 0
    tokens_processed: int = 0
    
    def complete(self, result: ToolResult, end_time: Optional[float] = None) -> None:
        """Mark execution as complete and record metrics."""
        self.end_time = end_time or time.time()
        self.duration = self.end_time - self.start_time
        self.status = result.status
        self.success = result.success
        
        if not result.success and result.data and isinstance(result.data, dict):
            self.error_message = result.data.get('error', 'Unknown error')
        
        # Estimate result size
        if result.data:
            self.result_size = len(str(result.data))


@dataclass
class ToolPerformanceStats:
    """Aggregated performance statistics for a tool."""
    
    tool_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    
    # Timing statistics
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    avg_duration: float = 0.0
    median_duration: float = 0.0
    
    # Success metrics
    success_rate: float = 0.0
    avg_confidence: float = 0.0
    
    # Resource usage
    avg_memory_usage: float = 0.0
    avg_cpu_usage: float = 0.0
    
    # Recent performance
    recent_executions: List[float] = field(default_factory=list)  # Last 100 durations
    performance_trend: str = "stable"  # improving, degrading, stable
    
    # Error patterns
    common_errors: Dict[str, int] = field(default_factory=dict)
    error_rate: float = 0.0
    
    # Usage patterns
    peak_usage_hours: List[int] = field(default_factory=list)
    request_patterns: Dict[str, int] = field(default_factory=dict)
    
    def update_from_execution(self, execution: ToolExecutionMetrics) -> None:
        """Update statistics from a new execution."""
        self.total_executions += 1
        
        if execution.success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
            if execution.error_message:
                self.common_errors[execution.error_message] = \
                    self.common_errors.get(execution.error_message, 0) + 1
        
        if execution.duration:
            self.total_duration += execution.duration
            self.min_duration = min(self.min_duration, execution.duration)
            self.max_duration = max(self.max_duration, execution.duration)
            self.avg_duration = self.total_duration / self.total_executions
            
            # Update recent executions (keep last 100)
            self.recent_executions.append(execution.duration)
            if len(self.recent_executions) > 100:
                self.recent_executions.pop(0)
            
            if len(self.recent_executions) >= 2:
                self.median_duration = statistics.median(self.recent_executions)
        
        # Update rates
        self.success_rate = self.successful_executions / self.total_executions if self.total_executions > 0 else 0.0
        self.error_rate = self.failed_executions / self.total_executions if self.total_executions > 0 else 0.0
        
        # Update confidence
        if execution.confidence_score > 0:
            total_confidence = (self.avg_confidence * (self.total_executions - 1) + execution.confidence_score)
            self.avg_confidence = total_confidence / self.total_executions
        
        # Update resource usage
        if execution.memory_usage:
            total_memory = (self.avg_memory_usage * (self.total_executions - 1) + execution.memory_usage)
            self.avg_memory_usage = total_memory / self.total_executions
        
        if execution.cpu_usage:
            total_cpu = (self.avg_cpu_usage * (self.total_executions - 1) + execution.cpu_usage)
            self.avg_cpu_usage = total_cpu / self.total_executions
        
        # Update performance trend
        self._update_performance_trend()
    
    def _update_performance_trend(self) -> None:
        """Analyze recent performance to determine trend."""
        if len(self.recent_executions) < 20:
            self.performance_trend = "insufficient_data"
            return
        
        # Compare recent 10 with previous 10
        recent_10 = self.recent_executions[-10:]
        previous_10 = self.recent_executions[-20:-10]
        
        recent_avg = statistics.mean(recent_10)
        previous_avg = statistics.mean(previous_10)
        
        # 10% threshold for trend detection
        threshold = previous_avg * 0.1
        
        if recent_avg < previous_avg - threshold:
            self.performance_trend = "improving"
        elif recent_avg > previous_avg + threshold:
            self.performance_trend = "degrading"
        else:
            self.performance_trend = "stable"


class ToolPerformanceMonitor:
    """Advanced performance monitoring system for Codexa tools."""
    
    def __init__(self, enable_resource_monitoring: bool = True):
        """Initialize the performance monitor."""
        self.logger = logging.getLogger("codexa.tools.performance")
        
        # Configuration
        self.enable_resource_monitoring = enable_resource_monitoring
        self.max_executions_history = 10000
        self.metrics_retention_days = 30
        
        # Storage
        self.execution_history: deque[ToolExecutionMetrics] = deque(maxlen=self.max_executions_history)
        self.tool_stats: Dict[str, ToolPerformanceStats] = {}
        self.active_executions: Dict[str, ToolExecutionMetrics] = {}
        
        # Analytics
        self.request_patterns: Dict[str, int] = defaultdict(int)
        self.tool_compatibility_matrix: Dict[Tuple[str, str], int] = defaultdict(int)  # (tool1, tool2) -> count
        self.performance_alerts: List[Dict[str, Any]] = []
        
        # Background monitoring
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Performance thresholds
        self.performance_thresholds = {
            'slow_execution': 5.0,      # seconds
            'high_error_rate': 0.15,    # 15%
            'memory_warning': 500.0,    # MB
            'cpu_warning': 80.0,        # %
        }
    
    def start_monitoring(self) -> None:
        """Start background performance monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._background_monitor,
            daemon=True
        )
        self.monitoring_thread.start()
        self.logger.info("Tool performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background performance monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
        self.executor.shutdown(wait=False)
        self.logger.info("Tool performance monitoring stopped")
    
    def start_execution(self, tool_name: str, request: str, context_size: int = 0) -> str:
        """Start tracking a tool execution."""
        execution_id = f"{tool_name}_{int(time.time() * 1000)}_{hash(request) % 10000}"
        
        execution = ToolExecutionMetrics(
            tool_name=tool_name,
            execution_id=execution_id,
            start_time=time.time(),
            request_text=request[:200],  # Truncate long requests
            context_size=context_size
        )
        
        self.active_executions[execution_id] = execution
        
        # Start resource monitoring if enabled
        if self.enable_resource_monitoring:
            self.executor.submit(self._monitor_execution_resources, execution_id)
        
        return execution_id
    
    def complete_execution(self, execution_id: str, result: ToolResult, confidence_score: float = 0.0) -> None:
        """Complete tracking a tool execution."""
        if execution_id not in self.active_executions:
            self.logger.warning(f"Unknown execution ID: {execution_id}")
            return
        
        execution = self.active_executions.pop(execution_id)
        execution.confidence_score = confidence_score
        execution.complete(result)
        
        # Store execution
        self.execution_history.append(execution)
        
        # Update tool statistics
        if execution.tool_name not in self.tool_stats:
            self.tool_stats[execution.tool_name] = ToolPerformanceStats(tool_name=execution.tool_name)
        
        self.tool_stats[execution.tool_name].update_from_execution(execution)
        
        # Update request patterns
        request_pattern = self._extract_request_pattern(execution.request_text)
        self.request_patterns[request_pattern] += 1
        
        # Check for performance alerts
        self._check_performance_alerts(execution)
        
        self.logger.debug(f"Completed execution tracking: {execution_id} ({execution.duration:.3f}s)")
    
    def get_tool_performance(self, tool_name: str) -> Optional[ToolPerformanceStats]:
        """Get performance statistics for a specific tool."""
        return self.tool_stats.get(tool_name)
    
    def get_system_performance(self) -> Dict[str, Any]:
        """Get overall system performance metrics."""
        if not self.execution_history:
            return {"status": "no_data"}
        
        total_executions = len(self.execution_history)
        successful = sum(1 for ex in self.execution_history if ex.success)
        failed = total_executions - successful
        
        durations = [ex.duration for ex in self.execution_history if ex.duration]
        
        return {
            "total_executions": total_executions,
            "success_rate": successful / total_executions if total_executions > 0 else 0.0,
            "error_rate": failed / total_executions if total_executions > 0 else 0.0,
            "avg_duration": statistics.mean(durations) if durations else 0.0,
            "median_duration": statistics.median(durations) if durations else 0.0,
            "total_tools": len(self.tool_stats),
            "active_executions": len(self.active_executions),
            "monitoring_active": self.monitoring_active,
            "performance_alerts": len(self.performance_alerts),
            "top_tools": self._get_top_performing_tools(5),
            "slowest_tools": self._get_slowest_tools(5),
            "request_patterns": dict(list(self.request_patterns.items())[:10])
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        system_performance = self.get_system_performance()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_period": "last_30_days",
            "system_overview": system_performance,
            "tool_details": {},
            "performance_trends": self._analyze_performance_trends(),
            "resource_usage": self._analyze_resource_usage(),
            "error_analysis": self._analyze_error_patterns(),
            "recommendations": self._generate_recommendations(),
            "alerts": self.performance_alerts[-20:],  # Last 20 alerts
        }
        
        # Add detailed tool statistics
        for tool_name, stats in self.tool_stats.items():
            report["tool_details"][tool_name] = asdict(stats)
        
        return report
    
    def export_metrics(self, file_path: str) -> bool:
        """Export performance metrics to JSON file."""
        try:
            report = self.get_performance_report()
            
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Performance metrics exported to: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return False
    
    def _background_monitor(self) -> None:
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Clean old data
                self._cleanup_old_data()
                
                # Check for stuck executions
                self._check_stuck_executions()
                
                # Update performance trends
                self._update_all_trends()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Background monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _monitor_execution_resources(self, execution_id: str) -> None:
        """Monitor resource usage for a specific execution."""
        try:
            import psutil
            process = psutil.Process()
            
            # Sample resource usage during execution
            samples = []
            start_time = time.time()
            
            while execution_id in self.active_executions and time.time() - start_time < 300:  # Max 5 min
                try:
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    
                    samples.append({
                        'cpu': cpu_percent,
                        'memory': memory_mb,
                        'timestamp': time.time()
                    })
                    
                    time.sleep(0.5)  # Sample every 500ms
                    
                except psutil.NoSuchProcess:
                    break
            
            # Update execution with average resource usage
            if execution_id in self.active_executions and samples:
                execution = self.active_executions[execution_id]
                execution.cpu_usage = statistics.mean([s['cpu'] for s in samples])
                execution.memory_usage = statistics.mean([s['memory'] for s in samples])
                
        except ImportError:
            # psutil not available, skip resource monitoring
            pass
        except Exception as e:
            self.logger.debug(f"Resource monitoring error: {e}")
    
    def _extract_request_pattern(self, request: str) -> str:
        """Extract a pattern from the request for analysis."""
        # Simple pattern extraction - could be enhanced with NLP
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['read', 'open', 'load']):
            return 'read_operation'
        elif any(word in request_lower for word in ['write', 'create', 'save']):
            return 'write_operation'
        elif any(word in request_lower for word in ['search', 'find', 'look']):
            return 'search_operation'
        elif any(word in request_lower for word in ['delete', 'remove', 'rm']):
            return 'delete_operation'
        elif any(word in request_lower for word in ['help', '?', 'how']):
            return 'help_request'
        else:
            return 'general_request'
    
    def _check_performance_alerts(self, execution: ToolExecutionMetrics) -> None:
        """Check if an execution triggers any performance alerts."""
        alerts = []
        
        # Slow execution alert
        if execution.duration and execution.duration > self.performance_thresholds['slow_execution']:
            alerts.append({
                'type': 'slow_execution',
                'tool': execution.tool_name,
                'duration': execution.duration,
                'threshold': self.performance_thresholds['slow_execution'],
                'timestamp': datetime.now().isoformat()
            })
        
        # High memory usage alert
        if execution.memory_usage and execution.memory_usage > self.performance_thresholds['memory_warning']:
            alerts.append({
                'type': 'high_memory',
                'tool': execution.tool_name,
                'memory_usage': execution.memory_usage,
                'threshold': self.performance_thresholds['memory_warning'],
                'timestamp': datetime.now().isoformat()
            })
        
        # High CPU usage alert
        if execution.cpu_usage and execution.cpu_usage > self.performance_thresholds['cpu_warning']:
            alerts.append({
                'type': 'high_cpu',
                'tool': execution.tool_name,
                'cpu_usage': execution.cpu_usage,
                'threshold': self.performance_thresholds['cpu_warning'],
                'timestamp': datetime.now().isoformat()
            })
        
        self.performance_alerts.extend(alerts)
        
        # Keep only recent alerts (last 1000)
        if len(self.performance_alerts) > 1000:
            self.performance_alerts = self.performance_alerts[-1000:]
    
    def _check_stuck_executions(self) -> None:
        """Check for executions that have been running too long."""
        current_time = time.time()
        stuck_threshold = 300  # 5 minutes
        
        stuck_executions = [
            exec_id for exec_id, execution in self.active_executions.items()
            if current_time - execution.start_time > stuck_threshold
        ]
        
        for exec_id in stuck_executions:
            execution = self.active_executions.pop(exec_id)
            self.logger.warning(f"Found stuck execution: {exec_id} ({execution.tool_name})")
            
            # Create alert
            self.performance_alerts.append({
                'type': 'stuck_execution',
                'tool': execution.tool_name,
                'execution_id': exec_id,
                'duration': current_time - execution.start_time,
                'timestamp': datetime.now().isoformat()
            })
    
    def _cleanup_old_data(self) -> None:
        """Clean up old performance data."""
        cutoff_time = time.time() - (self.metrics_retention_days * 24 * 3600)
        
        # Clean execution history
        while self.execution_history and self.execution_history[0].start_time < cutoff_time:
            self.execution_history.popleft()
        
        # Clean old alerts
        cutoff_datetime = datetime.now() - timedelta(days=7)  # Keep alerts for 7 days
        self.performance_alerts = [
            alert for alert in self.performance_alerts
            if datetime.fromisoformat(alert['timestamp']) > cutoff_datetime
        ]
    
    def _update_all_trends(self) -> None:
        """Update performance trends for all tools."""
        for stats in self.tool_stats.values():
            stats._update_performance_trend()
    
    def _get_top_performing_tools(self, count: int) -> List[Dict[str, Any]]:
        """Get top performing tools by success rate and speed."""
        tools = []
        
        for stats in self.tool_stats.values():
            if stats.total_executions >= 5:  # Minimum executions for reliability
                score = (stats.success_rate * 0.7) + (1.0 / (stats.avg_duration + 0.1) * 0.3)
                tools.append({
                    'name': stats.tool_name,
                    'score': score,
                    'success_rate': stats.success_rate,
                    'avg_duration': stats.avg_duration,
                    'executions': stats.total_executions
                })
        
        return sorted(tools, key=lambda x: x['score'], reverse=True)[:count]
    
    def _get_slowest_tools(self, count: int) -> List[Dict[str, Any]]:
        """Get slowest tools by average duration."""
        tools = []
        
        for stats in self.tool_stats.values():
            if stats.total_executions >= 3:
                tools.append({
                    'name': stats.tool_name,
                    'avg_duration': stats.avg_duration,
                    'max_duration': stats.max_duration,
                    'executions': stats.total_executions
                })
        
        return sorted(tools, key=lambda x: x['avg_duration'], reverse=True)[:count]
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze overall performance trends."""
        improving = sum(1 for stats in self.tool_stats.values() if stats.performance_trend == "improving")
        degrading = sum(1 for stats in self.tool_stats.values() if stats.performance_trend == "degrading")
        stable = sum(1 for stats in self.tool_stats.values() if stats.performance_trend == "stable")
        
        return {
            "improving_tools": improving,
            "degrading_tools": degrading,
            "stable_tools": stable,
            "tools_needing_attention": [
                stats.tool_name for stats in self.tool_stats.values()
                if stats.performance_trend == "degrading" or stats.error_rate > 0.1
            ]
        }
    
    def _analyze_resource_usage(self) -> Dict[str, Any]:
        """Analyze resource usage patterns."""
        recent_executions = list(self.execution_history)[-1000:]  # Last 1000 executions
        
        memory_usage = [ex.memory_usage for ex in recent_executions if ex.memory_usage]
        cpu_usage = [ex.cpu_usage for ex in recent_executions if ex.cpu_usage]
        
        return {
            "avg_memory_usage": statistics.mean(memory_usage) if memory_usage else 0,
            "peak_memory_usage": max(memory_usage) if memory_usage else 0,
            "avg_cpu_usage": statistics.mean(cpu_usage) if cpu_usage else 0,
            "peak_cpu_usage": max(cpu_usage) if cpu_usage else 0,
            "resource_intensive_tools": [
                stats.tool_name for stats in self.tool_stats.values()
                if stats.avg_memory_usage > 200 or stats.avg_cpu_usage > 50
            ]
        }
    
    def _analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns across tools."""
        all_errors = defaultdict(int)
        error_by_tool = defaultdict(dict)
        
        for stats in self.tool_stats.values():
            for error, count in stats.common_errors.items():
                all_errors[error] += count
                error_by_tool[stats.tool_name][error] = count
        
        return {
            "most_common_errors": dict(sorted(all_errors.items(), key=lambda x: x[1], reverse=True)[:10]),
            "tools_with_high_error_rate": [
                stats.tool_name for stats in self.tool_stats.values()
                if stats.error_rate > 0.15 and stats.total_executions >= 10
            ],
            "error_distribution": dict(error_by_tool)
        }
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Check for slow tools
        for stats in self.tool_stats.values():
            if stats.avg_duration > 3.0 and stats.total_executions >= 10:
                recommendations.append({
                    "type": "performance",
                    "tool": stats.tool_name,
                    "issue": f"Tool is slow (avg: {stats.avg_duration:.2f}s)",
                    "recommendation": "Consider optimizing implementation or adding caching"
                })
        
        # Check for unreliable tools
        for stats in self.tool_stats.values():
            if stats.error_rate > 0.15 and stats.total_executions >= 10:
                recommendations.append({
                    "type": "reliability",
                    "tool": stats.tool_name,
                    "issue": f"High error rate ({stats.error_rate:.1%})",
                    "recommendation": "Review error handling and input validation"
                })
        
        # Check for resource-intensive tools
        for stats in self.tool_stats.values():
            if stats.avg_memory_usage > 300:
                recommendations.append({
                    "type": "resource",
                    "tool": stats.tool_name,
                    "issue": f"High memory usage ({stats.avg_memory_usage:.1f}MB)",
                    "recommendation": "Optimize memory usage and consider streaming processing"
                })
        
        return recommendations
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "active": self.monitoring_active,
            "total_tools_monitored": len(self.tool_stats),
            "active_executions": len(self.active_executions),
            "execution_history_size": len(self.execution_history),
            "alerts_count": len(self.performance_alerts),
            "resource_monitoring_enabled": self.enable_resource_monitoring,
            "uptime": "monitoring_active"  # Could track actual uptime
        }