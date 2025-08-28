"""
Performance Dashboard Tool - Displays performance analytics and monitoring data
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus


class PerformanceDashboardTool(Tool):
    """Tool for displaying performance analytics and monitoring data"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def name(self) -> str:
        return "performance_dashboard"
    
    @property
    def description(self) -> str:
        return "Displays performance analytics, monitoring data, and system health metrics"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "show_performance_overview",
            "show_tool_statistics", 
            "show_system_health",
            "show_performance_alerts",
            "show_resource_usage",
            "show_error_analysis",
            "show_recommendations",
            "export_performance_report",
            "show_trends"
        ]
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the performance request"""
        request_lower = request.lower()
        
        # High confidence for explicit performance requests
        if any(word in request_lower for word in [
            'performance', 'analytics', 'monitoring', 'dashboard',
            'system health', 'tool statistics', 'performance report'
        ]):
            return 0.9
            
        # Medium confidence for metrics requests
        if any(word in request_lower for word in [
            'metrics', 'stats', 'statistics', 'health', 'status',
            'resource usage', 'errors', 'alerts'
        ]):
            return 0.7
            
        # Lower confidence for general analysis requests
        if any(word in request_lower for word in [
            'analyze', 'report', 'overview', 'trends'
        ]):
            return 0.4
            
        return 0.0
    
    def execute(self, request: str, context: ToolContext) -> ToolResult:
        """Execute performance dashboard request"""
        try:
            # Check if performance monitoring is available
            if not context.tool_manager or not hasattr(context.tool_manager, 'performance_monitor'):
                return ToolResult(
                    success=False,
                    data={'error': 'Performance monitoring not available'},
                    message="Performance monitoring is not enabled",
                    status=ToolStatus.ERROR
                )
            
            performance_monitor = context.tool_manager.performance_monitor
            if not performance_monitor:
                return ToolResult(
                    success=False,
                    data={'error': 'Performance monitor not initialized'},
                    message="Performance monitor is not initialized",
                    status=ToolStatus.ERROR
                )
            
            dashboard_type = self._parse_dashboard_request(request)
            
            # Route to appropriate dashboard handler
            handlers = {
                'overview': self._show_overview,
                'tools': self._show_tool_statistics,
                'health': self._show_system_health,
                'alerts': self._show_performance_alerts,
                'resources': self._show_resource_usage,
                'errors': self._show_error_analysis,
                'recommendations': self._show_recommendations,
                'export': self._export_report,
                'trends': self._show_trends
            }
            
            if dashboard_type not in handlers:
                dashboard_type = 'overview'  # Default
            
            result = handlers[dashboard_type](performance_monitor, context)
            
            return ToolResult(
                success=True,
                data=result,
                message=f"Performance {dashboard_type} displayed successfully",
                status=ToolStatus.SUCCESS
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Performance dashboard failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _parse_dashboard_request(self, request: str) -> str:
        """Parse request to determine dashboard type"""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['tool statistics', 'tool stats', 'tools']):
            return 'tools'
        elif any(word in request_lower for word in ['system health', 'health']):
            return 'health'
        elif any(word in request_lower for word in ['alerts', 'warnings']):
            return 'alerts'
        elif any(word in request_lower for word in ['resources', 'resource usage', 'memory', 'cpu']):
            return 'resources'
        elif any(word in request_lower for word in ['errors', 'error analysis']):
            return 'errors'
        elif any(word in request_lower for word in ['recommendations', 'suggestions']):
            return 'recommendations'
        elif any(word in request_lower for word in ['export', 'report']):
            return 'export'
        elif any(word in request_lower for word in ['trends', 'trending']):
            return 'trends'
        else:
            return 'overview'
    
    def _show_overview(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show performance overview"""
        system_perf = monitor.get_system_performance()
        monitoring_status = monitor.get_monitoring_status()
        
        overview = {
            'dashboard_type': 'overview',
            'timestamp': datetime.now().isoformat(),
            'monitoring_status': monitoring_status,
            'system_performance': system_perf,
            'summary': {
                'total_tools': system_perf.get('total_tools', 0),
                'total_executions': system_perf.get('total_executions', 0),
                'success_rate': f"{system_perf.get('success_rate', 0) * 100:.1f}%",
                'avg_duration': f"{system_perf.get('avg_duration', 0):.3f}s",
                'active_executions': system_perf.get('active_executions', 0),
                'performance_alerts': system_perf.get('performance_alerts', 0)
            }
        }
        
        return overview
    
    def _show_tool_statistics(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show detailed tool statistics"""
        system_perf = monitor.get_system_performance()
        
        # Get individual tool stats
        tool_details = {}
        for tool_name in system_perf.get('top_tools', []):
            tool_stats = monitor.get_tool_performance(tool_name['name'])
            if tool_stats:
                tool_details[tool_name['name']] = {
                    'executions': tool_stats.total_executions,
                    'success_rate': f"{tool_stats.success_rate * 100:.1f}%",
                    'avg_duration': f"{tool_stats.avg_duration:.3f}s",
                    'error_rate': f"{tool_stats.error_rate * 100:.1f}%",
                    'performance_trend': tool_stats.performance_trend,
                    'avg_confidence': f"{tool_stats.avg_confidence:.2f}"
                }
        
        return {
            'dashboard_type': 'tool_statistics',
            'timestamp': datetime.now().isoformat(),
            'top_performing_tools': system_perf.get('top_tools', [])[:10],
            'slowest_tools': system_perf.get('slowest_tools', [])[:10],
            'tool_details': tool_details,
            'total_tools_monitored': len(tool_details)
        }
    
    def _show_system_health(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show system health metrics"""
        system_perf = monitor.get_system_performance()
        monitoring_status = monitor.get_monitoring_status()
        
        # Determine health status
        success_rate = system_perf.get('success_rate', 0)
        avg_duration = system_perf.get('avg_duration', 0)
        alert_count = system_perf.get('performance_alerts', 0)
        
        if success_rate > 0.95 and avg_duration < 2.0 and alert_count < 5:
            health_status = 'excellent'
        elif success_rate > 0.85 and avg_duration < 5.0 and alert_count < 15:
            health_status = 'good'
        elif success_rate > 0.70 and avg_duration < 10.0 and alert_count < 30:
            health_status = 'fair'
        else:
            health_status = 'poor'
        
        return {
            'dashboard_type': 'system_health',
            'timestamp': datetime.now().isoformat(),
            'health_status': health_status,
            'health_score': int(success_rate * 100),
            'system_metrics': {
                'success_rate': f"{success_rate * 100:.1f}%",
                'avg_response_time': f"{avg_duration:.3f}s",
                'total_executions': system_perf.get('total_executions', 0),
                'active_executions': system_perf.get('active_executions', 0),
                'alert_count': alert_count
            },
            'monitoring_status': monitoring_status,
            'recommendations': self._get_health_recommendations(health_status, system_perf)
        }
    
    def _show_performance_alerts(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show performance alerts"""
        alerts = monitor.performance_alerts[-50:]  # Last 50 alerts
        
        # Group alerts by type
        alert_types = {}
        for alert in alerts:
            alert_type = alert.get('type', 'unknown')
            if alert_type not in alert_types:
                alert_types[alert_type] = []
            alert_types[alert_type].append(alert)
        
        return {
            'dashboard_type': 'performance_alerts',
            'timestamp': datetime.now().isoformat(),
            'total_alerts': len(alerts),
            'alert_types': {k: len(v) for k, v in alert_types.items()},
            'recent_alerts': alerts[-20:],  # Last 20 alerts
            'alerts_by_type': alert_types
        }
    
    def _show_resource_usage(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show resource usage analytics"""
        report = monitor.get_performance_report()
        resource_usage = report.get('resource_usage', {})
        
        return {
            'dashboard_type': 'resource_usage',
            'timestamp': datetime.now().isoformat(),
            'resource_metrics': resource_usage,
            'resource_intensive_tools': resource_usage.get('resource_intensive_tools', []),
            'memory_analysis': {
                'avg_usage': f"{resource_usage.get('avg_memory_usage', 0):.1f} MB",
                'peak_usage': f"{resource_usage.get('peak_memory_usage', 0):.1f} MB"
            },
            'cpu_analysis': {
                'avg_usage': f"{resource_usage.get('avg_cpu_usage', 0):.1f}%",
                'peak_usage': f"{resource_usage.get('peak_cpu_usage', 0):.1f}%"
            }
        }
    
    def _show_error_analysis(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show error analysis"""
        report = monitor.get_performance_report()
        error_analysis = report.get('error_analysis', {})
        
        return {
            'dashboard_type': 'error_analysis',
            'timestamp': datetime.now().isoformat(),
            'error_overview': error_analysis,
            'most_common_errors': error_analysis.get('most_common_errors', {}),
            'problematic_tools': error_analysis.get('tools_with_high_error_rate', []),
            'error_trends': 'Analysis would require time-series data'
        }
    
    def _show_recommendations(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show performance recommendations"""
        report = monitor.get_performance_report()
        recommendations = report.get('recommendations', [])
        
        # Group recommendations by type
        recommendation_groups = {'performance': [], 'reliability': [], 'resource': [], 'general': []}
        
        for rec in recommendations:
            rec_type = rec.get('type', 'general')
            if rec_type not in recommendation_groups:
                recommendation_groups[rec_type] = []
            recommendation_groups[rec_type].append(rec)
        
        return {
            'dashboard_type': 'recommendations',
            'timestamp': datetime.now().isoformat(),
            'total_recommendations': len(recommendations),
            'recommendations_by_type': recommendation_groups,
            'priority_actions': [rec for rec in recommendations if rec.get('type') in ['performance', 'reliability']][:5]
        }
    
    def _show_trends(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Show performance trends"""
        report = monitor.get_performance_report()
        trends = report.get('performance_trends', {})
        
        return {
            'dashboard_type': 'trends',
            'timestamp': datetime.now().isoformat(),
            'performance_trends': trends,
            'trending_analysis': {
                'improving_tools': trends.get('improving_tools', 0),
                'degrading_tools': trends.get('degrading_tools', 0),
                'stable_tools': trends.get('stable_tools', 0)
            },
            'attention_needed': trends.get('tools_needing_attention', [])
        }
    
    def _export_report(self, monitor, context: ToolContext) -> Dict[str, Any]:
        """Export comprehensive performance report"""
        report = monitor.get_performance_report()
        
        # Add export metadata
        report['export_info'] = {
            'exported_at': datetime.now().isoformat(),
            'exported_by': 'performance_dashboard_tool',
            'format': 'json',
            'version': self.version
        }
        
        return {
            'dashboard_type': 'export',
            'timestamp': datetime.now().isoformat(),
            'export_success': True,
            'report_size': len(str(report)),
            'full_report': report
        }
    
    def _get_health_recommendations(self, health_status: str, system_perf: Dict[str, Any]) -> List[str]:
        """Get health-based recommendations"""
        recommendations = []
        
        if health_status == 'poor':
            recommendations.extend([
                "Review and optimize slow-performing tools",
                "Investigate high error rates and fix underlying issues", 
                "Consider increasing system resources",
                "Review recent performance alerts for patterns"
            ])
        elif health_status == 'fair':
            recommendations.extend([
                "Monitor performance trends closely",
                "Optimize tools with high error rates",
                "Consider proactive maintenance"
            ])
        elif health_status == 'good':
            recommendations.extend([
                "Continue monitoring current performance",
                "Look for optimization opportunities"
            ])
        else:  # excellent
            recommendations.extend([
                "System performing optimally",
                "Consider sharing best practices"
            ])
        
        return recommendations
    
    def get_status(self) -> Dict[str, Any]:
        """Get performance dashboard tool status"""
        return {
            'tool_name': self.name,
            'version': self.version,
            'capabilities': self.capabilities,
            'dashboard_types': [
                'overview', 'tools', 'health', 'alerts', 
                'resources', 'errors', 'recommendations', 
                'export', 'trends'
            ]
        }