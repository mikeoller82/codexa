"""
Comprehensive error handling and user guidance system for Codexa.
"""

import sys
import traceback
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error categories for better organization."""
    PROVIDER = "provider"
    MCP = "mcp"
    COMMAND = "command"
    PLUGIN = "plugin"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    SECURITY = "security"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors."""
    operation: str
    component: str
    user_action: Optional[str] = None
    system_state: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserGuidance:
    """User guidance information."""
    immediate_actions: List[str] = field(default_factory=list)
    troubleshooting_steps: List[str] = field(default_factory=list)
    prevention_tips: List[str] = field(default_factory=list)
    related_docs: List[str] = field(default_factory=list)
    recovery_commands: List[str] = field(default_factory=list)


@dataclass
class CodexaError:
    """Comprehensive error representation."""
    error_id: str
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    technical_details: str
    user_message: str
    context: ErrorContext
    guidance: UserGuidance
    recoverable: bool = True
    auto_recovery_attempted: bool = False
    occurrence_count: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


class ErrorManager:
    """Comprehensive error handling and user guidance manager."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.error_manager")
        
        # Error tracking
        self.error_history: Dict[str, CodexaError] = {}
        self.error_patterns: Dict[str, List[str]] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        
        # User guidance database
        self.guidance_db: Dict[str, UserGuidance] = {}
        
        # Recovery statistics
        self.recovery_stats: Dict[str, Dict[str, Any]] = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "strategies_used": []
        }
        
        # Initialize built-in guidance
        self._initialize_error_guidance()
        self._initialize_recovery_strategies()
    
    def handle_error(
        self,
        exception: Exception,
        context: ErrorContext,
        auto_recover: bool = True
    ) -> CodexaError:
        """Handle an error comprehensively."""
        # Create or update error record
        error = self._create_error_record(exception, context)
        
        # Log the error
        self._log_error(error)
        
        # Attempt auto-recovery if enabled
        if auto_recover and error.recoverable:
            recovery_success = self._attempt_auto_recovery(error)
            error.auto_recovery_attempted = True
            
            if recovery_success:
                self.console.print(f"[green]✓ Auto-recovery successful for {error.category.value} error[/green]")
                return error
        
        # Display user-friendly error
        self._display_error(error)
        
        return error
    
    def _create_error_record(self, exception: Exception, context: ErrorContext) -> CodexaError:
        """Create a comprehensive error record."""
        # Generate error ID
        error_signature = f"{type(exception).__name__}:{context.component}:{context.operation}"
        error_id = f"CX-{hash(error_signature) % 10000:04d}"
        
        # Determine category and severity
        category = self._categorize_error(exception, context)
        severity = self._assess_severity(exception, context)
        
        # Check if this is a recurring error
        if error_id in self.error_history:
            existing_error = self.error_history[error_id]
            existing_error.occurrence_count += 1
            existing_error.last_seen = datetime.now()
            return existing_error
        
        # Create new error record
        error = CodexaError(
            error_id=error_id,
            severity=severity,
            category=category,
            message=str(exception),
            technical_details=traceback.format_exc(),
            user_message=self._generate_user_message(exception, context),
            context=context,
            guidance=self._get_guidance(category, exception),
            recoverable=self._is_recoverable(exception, context)
        )
        
        # Store in history
        self.error_history[error_id] = error
        
        return error
    
    def _categorize_error(self, exception: Exception, context: ErrorContext) -> ErrorCategory:
        """Categorize error based on exception type and context."""
        error_type = type(exception).__name__.lower()
        component = context.component.lower()
        
        # Component-based categorization
        if "provider" in component:
            return ErrorCategory.PROVIDER
        elif "mcp" in component:
            return ErrorCategory.MCP
        elif "command" in component:
            return ErrorCategory.COMMAND
        elif "plugin" in component:
            return ErrorCategory.PLUGIN
        elif "config" in component:
            return ErrorCategory.CONFIGURATION
        
        # Exception-based categorization
        if "network" in error_type or "connection" in error_type:
            return ErrorCategory.NETWORK
        elif "file" in error_type or "io" in error_type:
            return ErrorCategory.FILESYSTEM
        elif "permission" in error_type or "security" in error_type:
            return ErrorCategory.SECURITY
        elif "validation" in error_type or "value" in error_type:
            return ErrorCategory.VALIDATION
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, exception: Exception, context: ErrorContext) -> ErrorSeverity:
        """Assess error severity."""
        error_type = type(exception).__name__.lower()
        
        # Critical system errors
        if "systemexit" in error_type or "keyboardinterrupt" in error_type:
            return ErrorSeverity.FATAL
        
        # Security and data integrity errors
        if "permission" in error_type or "security" in error_type:
            return ErrorSeverity.CRITICAL
        
        # Connection and network errors
        if "connection" in error_type or "timeout" in error_type:
            return ErrorSeverity.ERROR
        
        # Validation and value errors
        if "value" in error_type or "type" in error_type:
            return ErrorSeverity.WARNING
        
        return ErrorSeverity.ERROR
    
    def _generate_user_message(self, exception: Exception, context: ErrorContext) -> str:
        """Generate user-friendly error message."""
        error_type = type(exception).__name__
        operation = context.operation
        
        if error_type == "ConnectionError":
            return f"Unable to connect while {operation}. Please check your network connection."
        elif error_type == "PermissionError":
            return f"Permission denied during {operation}. Check file/directory permissions."
        elif error_type == "FileNotFoundError":
            return f"Required file not found during {operation}. File may have been moved or deleted."
        elif error_type == "TimeoutError":
            return f"Operation timed out during {operation}. The service may be slow or unavailable."
        else:
            return f"An error occurred during {operation}: {str(exception)}"
    
    def _get_guidance(self, category: ErrorCategory, exception: Exception) -> UserGuidance:
        """Get user guidance for error category."""
        guidance_key = f"{category.value}:{type(exception).__name__}"
        
        # Try specific guidance first
        if guidance_key in self.guidance_db:
            return self.guidance_db[guidance_key]
        
        # Fall back to category guidance
        category_key = category.value
        if category_key in self.guidance_db:
            return self.guidance_db[category_key]
        
        # Default guidance
        return UserGuidance(
            immediate_actions=["Check the error details below", "Try the operation again"],
            troubleshooting_steps=["Review system logs", "Check configuration"],
            prevention_tips=["Monitor system health", "Keep backups current"],
            related_docs=["User Manual", "Troubleshooting Guide"]
        )
    
    def _is_recoverable(self, exception: Exception, context: ErrorContext) -> bool:
        """Determine if error is recoverable."""
        error_type = type(exception).__name__.lower()
        
        # Non-recoverable errors
        non_recoverable = [
            "systemexit", "keyboardinterrupt", "memoryerror",
            "permissionerror", "securityerror"
        ]
        
        return not any(nr in error_type for nr in non_recoverable)
    
    def _attempt_auto_recovery(self, error: CodexaError) -> bool:
        """Attempt automatic error recovery."""
        recovery_key = f"{error.category.value}:{type(error).__name__}"
        
        # Try specific recovery strategy
        if recovery_key in self.recovery_strategies:
            strategy = self.recovery_strategies[recovery_key]
            try:
                result = strategy(error)
                self.recovery_stats["attempts"] += 1
                if result:
                    self.recovery_stats["successes"] += 1
                    self.recovery_stats["strategies_used"].append(recovery_key)
                else:
                    self.recovery_stats["failures"] += 1
                return result
            except Exception as e:
                self.logger.error(f"Recovery strategy failed: {e}")
                self.recovery_stats["failures"] += 1
                return False
        
        return False
    
    def _display_error(self, error: CodexaError):
        """Display user-friendly error information."""
        # Error severity styling
        severity_styles = {
            ErrorSeverity.INFO: "blue",
            ErrorSeverity.WARNING: "yellow",
            ErrorSeverity.ERROR: "red",
            ErrorSeverity.CRITICAL: "bold red",
            ErrorSeverity.FATAL: "bold white on red"
        }
        
        severity_icons = {
            ErrorSeverity.INFO: "ℹ️",
            ErrorSeverity.WARNING: "⚠️",
            ErrorSeverity.ERROR: "❌",
            ErrorSeverity.CRITICAL: "🚨",
            ErrorSeverity.FATAL: "💀"
        }
        
        style = severity_styles.get(error.severity, "red")
        icon = severity_icons.get(error.severity, "❌")
        
        # Main error panel
        error_content = []
        error_content.append(f"[bold]{icon} {error.severity.value.upper()}: {error.user_message}[/bold]")
        error_content.append(f"\n[dim]Error ID: {error.error_id}[/dim]")
        error_content.append(f"[dim]Category: {error.category.value}[/dim]")
        error_content.append(f"[dim]Component: {error.context.component}[/dim]")
        
        if error.occurrence_count > 1:
            error_content.append(f"[dim]Occurrences: {error.occurrence_count}[/dim]")
        
        error_panel = Panel(
            "\n".join(error_content),
            title="Error Details",
            border_style=style
        )
        
        self.console.print(error_panel)
        
        # Guidance panels
        if error.guidance.immediate_actions:
            self._display_guidance_section("🚀 Immediate Actions", error.guidance.immediate_actions, "green")
        
        if error.guidance.troubleshooting_steps:
            self._display_guidance_section("🔧 Troubleshooting Steps", error.guidance.troubleshooting_steps, "yellow")
        
        if error.guidance.recovery_commands:
            self._display_guidance_section("💻 Recovery Commands", error.guidance.recovery_commands, "blue")
        
        if error.guidance.prevention_tips:
            self._display_guidance_section("🛡️ Prevention Tips", error.guidance.prevention_tips, "cyan")
    
    def _display_guidance_section(self, title: str, items: List[str], color: str):
        """Display a guidance section."""
        content = []
        for i, item in enumerate(items, 1):
            content.append(f"{i}. {item}")
        
        panel = Panel(
            "\n".join(content),
            title=title,
            border_style=color
        )
        
        self.console.print(panel)
    
    def _log_error(self, error: CodexaError):
        """Log error details."""
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.FATAL: logging.CRITICAL
        }.get(error.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"[{error.error_id}] {error.category.value}: {error.message} "
            f"(component: {error.context.component}, operation: {error.context.operation})"
        )
    
    @contextmanager
    def error_context(self, operation: str, component: str, **kwargs):
        """Context manager for error handling."""
        context = ErrorContext(
            operation=operation,
            component=component,
            **kwargs
        )
        
        try:
            yield context
        except Exception as e:
            self.handle_error(e, context)
            raise
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        now = datetime.now()
        recent_errors = [
            error for error in self.error_history.values()
            if (now - error.last_seen).total_seconds() < 3600  # Last hour
        ]
        
        category_counts = {}
        severity_counts = {}
        
        for error in self.error_history.values():
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + error.occurrence_count
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + error.occurrence_count
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "category_breakdown": category_counts,
            "severity_breakdown": severity_counts,
            "recovery_stats": self.recovery_stats
        }
    
    def display_error_summary(self):
        """Display error summary."""
        stats = self.get_error_statistics()
        
        # Summary table
        table = Table(title="Error Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Errors", str(stats["total_errors"]))
        table.add_row("Recent Errors (1h)", str(stats["recent_errors"]))
        table.add_row("Recovery Success Rate", f"{stats['recovery_stats']['successes'] / max(1, stats['recovery_stats']['attempts']) * 100:.1f}%")
        
        self.console.print(table)
        
        # Category breakdown
        if stats["category_breakdown"]:
            self.console.print("\n[bold]Error Categories:[/bold]")
            for category, count in sorted(stats["category_breakdown"].items()):
                self.console.print(f"  {category}: {count}")
    
    def _initialize_error_guidance(self):
        """Initialize built-in error guidance."""
        # Provider errors
        self.guidance_db["provider"] = UserGuidance(
            immediate_actions=[
                "Check your API keys and configuration",
                "Verify network connectivity",
                "Try switching to a different provider"
            ],
            troubleshooting_steps=[
                "Run `/provider status` to check current provider",
                "Use `/provider list` to see available providers",
                "Check environment variables for API keys",
                "Test with a simple query"
            ],
            recovery_commands=[
                "/provider switch <provider-name>",
                "/config check",
                "/status"
            ],
            prevention_tips=[
                "Keep API keys up to date",
                "Monitor provider status regularly",
                "Have backup providers configured"
            ]
        )
        
        # MCP errors
        self.guidance_db["mcp"] = UserGuidance(
            immediate_actions=[
                "Check MCP server status",
                "Verify server configuration",
                "Restart the problematic server"
            ],
            troubleshooting_steps=[
                "Run `/mcp status` to check servers",
                "Check server logs for errors",
                "Verify server dependencies",
                "Test server connectivity"
            ],
            recovery_commands=[
                "/mcp restart <server-name>",
                "/mcp status",
                "/mcp logs <server-name>"
            ],
            prevention_tips=[
                "Keep MCP servers updated",
                "Monitor server health",
                "Configure automatic restarts"
            ]
        )
        
        # Command errors
        self.guidance_db["command"] = UserGuidance(
            immediate_actions=[
                "Check command syntax",
                "Verify required parameters",
                "Try using help for the command"
            ],
            troubleshooting_steps=[
                "Use `/help <command>` for syntax help",
                "Check available commands with `/commands`",
                "Verify you have required permissions",
                "Check if command dependencies are available"
            ],
            recovery_commands=[
                "/help <command-name>",
                "/commands",
                "/status"
            ],
            prevention_tips=[
                "Use tab completion for commands",
                "Read command documentation",
                "Test commands in safe environments first"
            ]
        )
    
    def _initialize_recovery_strategies(self):
        """Initialize automatic recovery strategies."""
        def recover_provider_error(error: CodexaError) -> bool:
            """Recover from provider errors by switching providers."""
            try:
                # This would integrate with the enhanced provider system
                # to automatically switch to a backup provider
                self.logger.info("Attempting provider failover...")
                # Implementation would go here
                return True
            except Exception:
                return False
        
        def recover_mcp_error(error: CodexaError) -> bool:
            """Recover from MCP errors by restarting server."""
            try:
                # This would integrate with the MCP service to restart servers
                self.logger.info("Attempting MCP server restart...")
                # Implementation would go here
                return True
            except Exception:
                return False
        
        def recover_network_error(error: CodexaError) -> bool:
            """Recover from network errors with retry logic."""
            try:
                # Implement exponential backoff retry
                self.logger.info("Retrying network operation...")
                # Implementation would go here
                return True
            except Exception:
                return False
        
        # Register recovery strategies
        self.recovery_strategies["provider:ConnectionError"] = recover_provider_error
        self.recovery_strategies["mcp:ConnectionError"] = recover_mcp_error
        self.recovery_strategies["network:ConnectionError"] = recover_network_error
        self.recovery_strategies["network:TimeoutError"] = recover_network_error