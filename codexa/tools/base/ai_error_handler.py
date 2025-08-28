"""
AI-aware error handling and resilience system for Codexa tools.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .tool_interface import ToolResult, ToolContext


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Recovery strategy types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    DEGRADE = "degrade"
    ABORT = "abort"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    tool_name: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    context: ToolContext
    timestamp: datetime
    retry_count: int = 0
    recovery_attempted: bool = False


class AIErrorHandler:
    """
    Advanced error handling system with AI-aware recovery strategies.
    
    Features:
    - Provider-specific error handling
    - Intelligent retry with exponential backoff
    - Automatic fallback to alternative tools/providers
    - Error pattern analysis and learning
    - Graceful degradation strategies
    """
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger("codexa.tools.error_handler")
        
        # Error tracking
        self._error_history: List[ErrorContext] = []
        self._error_patterns: Dict[str, int] = {}
        self._provider_failures: Dict[str, List[datetime]] = {}
        
        # Recovery configuration
        self._max_retries = 3
        self._retry_delays = [1, 2, 5]  # Exponential backoff
        self._provider_cooldown = timedelta(minutes=5)
        
        # Error type mappings
        self._error_severity_map = {
            "ConnectionError": ErrorSeverity.HIGH,
            "TimeoutError": ErrorSeverity.MEDIUM,
            "AuthenticationError": ErrorSeverity.HIGH,
            "RateLimitError": ErrorSeverity.MEDIUM,
            "APIError": ErrorSeverity.MEDIUM,
            "ProviderError": ErrorSeverity.HIGH,
            "ValidationError": ErrorSeverity.LOW,
            "ConfigurationError": ErrorSeverity.HIGH,
        }
    
    async def handle_error(self, 
                          tool_name: str,
                          error: Exception,
                          context: ToolContext,
                          tool_result: Optional[ToolResult] = None) -> ToolResult:
        """
        Handle error with intelligent recovery strategies.
        
        Args:
            tool_name: Name of tool that failed
            error: Exception that occurred
            context: Tool execution context
            tool_result: Optional existing tool result
            
        Returns:
            ToolResult with error handled or recovery attempted
        """
        try:
            # Create error context
            error_context = self._create_error_context(tool_name, error, context)
            
            # Log and track the error
            self._track_error(error_context)
            
            # Determine recovery strategy
            recovery_strategy = self._determine_recovery_strategy(error_context)
            
            # Execute recovery
            recovery_result = await self._execute_recovery(error_context, recovery_strategy)
            
            if recovery_result and recovery_result.success:
                self.logger.info(f"Successfully recovered from error in {tool_name} using {recovery_strategy.value}")
                return recovery_result
            
            # If recovery failed, return graceful error
            return self._create_graceful_error_result(error_context, recovery_strategy)
            
        except Exception as handler_error:
            self.logger.error(f"Error handler failed: {handler_error}")
            return ToolResult.error_result(
                error=f"Error handling failed: {str(error)}",
                tool_name=tool_name
            )
    
    def _create_error_context(self, tool_name: str, error: Exception, context: ToolContext) -> ErrorContext:
        """Create error context from exception."""
        error_type = error.__class__.__name__
        error_message = str(error)
        severity = self._determine_error_severity(error_type, error_message)
        
        return ErrorContext(
            tool_name=tool_name,
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            context=context,
            timestamp=datetime.now()
        )
    
    def _determine_error_severity(self, error_type: str, error_message: str) -> ErrorSeverity:
        """Determine error severity based on type and message."""
        # Check explicit mappings
        if error_type in self._error_severity_map:
            return self._error_severity_map[error_type]
        
        # Check message patterns
        message_lower = error_message.lower()
        
        if any(pattern in message_lower for pattern in ["critical", "fatal", "emergency"]):
            return ErrorSeverity.CRITICAL
        elif any(pattern in message_lower for pattern in ["authentication", "authorization", "forbidden"]):
            return ErrorSeverity.HIGH
        elif any(pattern in message_lower for pattern in ["timeout", "rate limit", "quota"]):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _track_error(self, error_context: ErrorContext) -> None:
        """Track error for pattern analysis."""
        # Add to history
        self._error_history.append(error_context)
        
        # Track patterns
        pattern = f"{error_context.tool_name}:{error_context.error_type}"
        self._error_patterns[pattern] = self._error_patterns.get(pattern, 0) + 1
        
        # Track provider failures for AI tools
        if error_context.tool_name.startswith("ai_") and error_context.context.provider:
            provider_name = error_context.context.provider.__class__.__name__
            if provider_name not in self._provider_failures:
                self._provider_failures[provider_name] = []
            self._provider_failures[provider_name].append(error_context.timestamp)
        
        # Maintain history limit
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-1000:]
        
        self.logger.warning(f"Error tracked: {error_context.tool_name} - {error_context.error_type}: {error_context.error_message}")
    
    def _determine_recovery_strategy(self, error_context: ErrorContext) -> RecoveryStrategy:
        """Determine best recovery strategy for the error."""
        
        # Critical errors - abort immediately
        if error_context.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ABORT
        
        # Check error patterns for strategy hints
        error_type = error_context.error_type
        
        # Network and timeout errors - retry
        if error_type in ["ConnectionError", "TimeoutError", "NetworkError"]:
            if error_context.retry_count < self._max_retries:
                return RecoveryStrategy.RETRY
            else:
                return RecoveryStrategy.FALLBACK
        
        # Rate limiting - wait and retry or fallback
        if error_type in ["RateLimitError", "QuotaExceededError"]:
            return RecoveryStrategy.FALLBACK
        
        # Authentication errors - fallback immediately
        if error_type in ["AuthenticationError", "AuthorizationError"]:
            return RecoveryStrategy.FALLBACK
        
        # Provider-specific errors for AI tools
        if error_context.tool_name.startswith("ai_"):
            if error_type in ["APIError", "ProviderError"]:
                return RecoveryStrategy.FALLBACK
        
        # Default: retry if not too many attempts
        if error_context.retry_count < self._max_retries:
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.DEGRADE
    
    async def _execute_recovery(self, error_context: ErrorContext, strategy: RecoveryStrategy) -> Optional[ToolResult]:
        """Execute recovery strategy."""
        
        try:
            if strategy == RecoveryStrategy.RETRY:
                return await self._retry_with_backoff(error_context)
            
            elif strategy == RecoveryStrategy.FALLBACK:
                return await self._fallback_to_alternative(error_context)
            
            elif strategy == RecoveryStrategy.DEGRADE:
                return await self._graceful_degradation(error_context)
            
            else:  # ABORT
                return None
                
        except Exception as recovery_error:
            self.logger.error(f"Recovery execution failed: {recovery_error}")
            return None
    
    async def _retry_with_backoff(self, error_context: ErrorContext) -> Optional[ToolResult]:
        """Retry operation with exponential backoff."""
        
        if error_context.retry_count >= self._max_retries:
            return None
        
        # Calculate delay
        delay = self._retry_delays[min(error_context.retry_count, len(self._retry_delays) - 1)]
        
        self.logger.info(f"Retrying {error_context.tool_name} in {delay}s (attempt {error_context.retry_count + 1})")
        
        # Wait before retry
        await asyncio.sleep(delay)
        
        # Update retry count
        error_context.retry_count += 1
        
        # Note: Actual retry would need to be handled by the tool manager
        # This is a signal that retry should be attempted
        return ToolResult.success_result(
            data={"retry_requested": True, "delay": delay},
            tool_name="error_handler",
            output=f"Retry requested for {error_context.tool_name}"
        )
    
    async def _fallback_to_alternative(self, error_context: ErrorContext) -> Optional[ToolResult]:
        """Fallback to alternative tools or providers."""
        
        fallback_suggestions = []
        
        # AI tool fallbacks
        if error_context.tool_name.startswith("ai_"):
            fallback_suggestions = self._get_ai_tool_fallbacks(error_context.tool_name)
        
        # General tool fallbacks
        else:
            fallback_suggestions = self._get_general_tool_fallbacks(error_context.tool_name)
        
        if fallback_suggestions:
            self.logger.info(f"Suggesting fallback tools for {error_context.tool_name}: {fallback_suggestions}")
            
            return ToolResult.success_result(
                data={
                    "fallback_requested": True,
                    "fallback_tools": fallback_suggestions,
                    "original_error": error_context.error_message
                },
                tool_name="error_handler",
                output=f"Fallback suggested for {error_context.tool_name}"
            )
        
        return None
    
    def _get_ai_tool_fallbacks(self, tool_name: str) -> List[str]:
        """Get fallback suggestions for AI tools."""
        fallbacks = {
            "ai_text_generation": ["ai_provider", "conversational_tool"],
            "ai_code_generation": ["ai_provider", "ai_text_generation"],
            "ai_analysis": ["ai_provider", "ai_text_generation"],
            "ai_provider": ["conversational_tool"]
        }
        
        return fallbacks.get(tool_name, ["conversational_tool"])
    
    def _get_general_tool_fallbacks(self, tool_name: str) -> List[str]:
        """Get fallback suggestions for general tools."""
        # This could be expanded based on tool capabilities
        return []
    
    async def _graceful_degradation(self, error_context: ErrorContext) -> Optional[ToolResult]:
        """Provide graceful degradation response."""
        
        degraded_response = self._create_degraded_response(error_context)
        
        return ToolResult.success_result(
            data={
                "degraded_mode": True,
                "degraded_response": degraded_response,
                "original_error": error_context.error_message
            },
            tool_name="error_handler",
            output=degraded_response
        )
    
    def _create_degraded_response(self, error_context: ErrorContext) -> str:
        """Create a helpful degraded response."""
        
        if error_context.tool_name.startswith("ai_"):
            return (
                f"I apologize, but I'm currently unable to process your AI request due to a {error_context.error_type}. "
                f"This might be due to provider issues or connectivity problems. "
                f"Please try again later or rephrase your request."
            )
        
        return (
            f"I encountered an issue with the {error_context.tool_name} tool. "
            f"The error was: {error_context.error_message}. "
            f"Please try a different approach or contact support if the issue persists."
        )
    
    def _create_graceful_error_result(self, error_context: ErrorContext, recovery_strategy: RecoveryStrategy) -> ToolResult:
        """Create a graceful error result with helpful information."""
        
        error_guidance = self._get_error_guidance(error_context)
        
        return ToolResult.error_result(
            error=f"{error_context.error_message}",
            tool_name=error_context.tool_name,
            data={
                "error_context": {
                    "type": error_context.error_type,
                    "severity": error_context.severity.value,
                    "recovery_attempted": recovery_strategy.value,
                    "guidance": error_guidance
                }
            }
        )
    
    def _get_error_guidance(self, error_context: ErrorContext) -> str:
        """Get helpful guidance for the user based on error type."""
        
        error_type = error_context.error_type
        
        guidance_map = {
            "ConnectionError": "Check your internet connection and try again.",
            "TimeoutError": "The operation timed out. Try again or simplify your request.",
            "AuthenticationError": "Check your API keys and authentication settings.",
            "RateLimitError": "You've hit rate limits. Please wait and try again later.",
            "ConfigurationError": "Check your configuration settings.",
            "ValidationError": "Please check your input and try again."
        }
        
        return guidance_map.get(error_type, "Please try again or contact support if the issue persists.")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        
        recent_errors = [e for e in self._error_history if (datetime.now() - e.timestamp).days < 1]
        
        return {
            "total_errors": len(self._error_history),
            "recent_errors": len(recent_errors),
            "error_patterns": dict(sorted(self._error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
            "provider_failures": {
                provider: len(failures) 
                for provider, failures in self._provider_failures.items()
            },
            "severity_distribution": {
                severity.value: len([e for e in recent_errors if e.severity == severity])
                for severity in ErrorSeverity
            }
        }
    
    def is_provider_healthy(self, provider_name: str) -> bool:
        """Check if a provider is healthy based on recent failures."""
        
        if provider_name not in self._provider_failures:
            return True
        
        recent_failures = [
            failure for failure in self._provider_failures[provider_name]
            if datetime.now() - failure < self._provider_cooldown
        ]
        
        # Provider is unhealthy if more than 3 failures in cooldown period
        return len(recent_failures) < 3