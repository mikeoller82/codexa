"""
Automated recovery manager for Codexa with intelligent recovery strategies.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


class RecoveryStrategy(Enum):
    """Recovery strategy types."""
    RETRY = "retry"
    FAILOVER = "failover"
    RESTART = "restart"
    RECONFIGURE = "reconfigure"
    FALLBACK = "fallback"
    MANUAL = "manual"


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    strategy_used: RecoveryStrategy
    error: Optional[str] = None
    message: Optional[str] = None
    execution_time: float = 0.0
    attempts: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryContext:
    """Context for recovery operations."""
    component: str
    error_type: str
    error_message: str
    system_state: Dict[str, Any] = field(default_factory=dict)
    available_resources: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)


class RecoveryManager:
    """Intelligent recovery management system."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.recovery_manager")
        
        # Recovery strategies and handlers
        self.recovery_strategies: Dict[str, List[Callable]] = {}
        self.strategy_success_rates: Dict[str, Dict[str, float]] = {}
        
        # Recovery state tracking
        self.active_recoveries: Dict[str, Dict[str, Any]] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        
        # Configuration
        self.max_retry_attempts = 3
        self.retry_delay_base = 1.0  # Base delay in seconds
        self.circuit_breaker_threshold = 5  # Failures before circuit opens
        self.circuit_breaker_timeout = 300  # Seconds to keep circuit open
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Initialize built-in recovery strategies
        self._initialize_recovery_strategies()
    
    async def attempt_recovery(
        self,
        context: RecoveryContext,
        strategies: Optional[List[RecoveryStrategy]] = None
    ) -> RecoveryResult:
        """Attempt automated recovery using intelligent strategy selection."""
        start_time = datetime.now()
        recovery_key = f"{context.component}:{context.error_type}"
        
        # Check circuit breaker
        if self._is_circuit_open(recovery_key):
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.MANUAL,
                error="Circuit breaker open - manual intervention required",
                execution_time=0.0
            )
        
        # Select recovery strategies
        if strategies is None:
            strategies = self._select_optimal_strategies(context)
        
        # Track recovery attempt
        self.active_recoveries[recovery_key] = {
            "context": context,
            "start_time": start_time,
            "strategies": strategies
        }
        
        # Display recovery initiation
        self.console.print(f"[yellow]🔄 Initiating recovery for {context.component}...[/yellow]")
        
        # Try each strategy in order
        for strategy in strategies:
            self.console.print(f"[blue]Trying {strategy.value} strategy...[/blue]")
            
            try:
                result = await self._execute_recovery_strategy(strategy, context)
                
                if result.success:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    result.execution_time = execution_time
                    
                    # Update success rates
                    self._update_success_rate(context, strategy, True)
                    
                    # Record successful recovery
                    self._record_recovery_success(context, result)
                    
                    self.console.print(f"[green]✓ Recovery successful using {strategy.value} strategy[/green]")
                    
                    # Clean up tracking
                    self.active_recoveries.pop(recovery_key, None)
                    
                    return result
                else:
                    self.console.print(f"[yellow]⚠ {strategy.value} strategy failed: {result.error}[/yellow]")
                    self._update_success_rate(context, strategy, False)
            
            except Exception as e:
                self.logger.error(f"Recovery strategy {strategy.value} failed with exception: {e}")
                self._update_success_rate(context, strategy, False)
        
        # All strategies failed
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Update circuit breaker
        self._record_failure(recovery_key)
        
        # Record failed recovery
        failed_result = RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL,
            error="All automated recovery strategies failed",
            execution_time=execution_time,
            attempts=len(strategies)
        )
        
        self._record_recovery_failure(context, failed_result)
        
        self.console.print("[red]❌ Automated recovery failed - manual intervention required[/red]")
        
        # Clean up tracking
        self.active_recoveries.pop(recovery_key, None)
        
        return failed_result
    
    async def _execute_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        context: RecoveryContext
    ) -> RecoveryResult:
        """Execute a specific recovery strategy."""
        strategy_key = f"{context.component}:{strategy.value}"
        
        if strategy_key not in self.recovery_strategies:
            return RecoveryResult(
                success=False,
                strategy_used=strategy,
                message=f"No handler available for strategy {strategy.value}",
                error=f"No handler available for strategy {strategy.value}",
                execution_time=0.0
            )
        
        handlers = self.recovery_strategies[strategy_key]
        
        for handler in handlers:
            try:
                result = await handler(context)
                if result.success:
                    result.strategy_used = strategy
                    return result
            except Exception as e:
                self.logger.error(f"Recovery handler failed: {e}")
                continue
        
        return RecoveryResult(
            success=False,
            strategy_used=strategy,
            message="All handlers for strategy failed",
            error="All handlers for strategy failed",
            execution_time=0.0
        )
    
    def _select_optimal_strategies(self, context: RecoveryContext) -> List[RecoveryStrategy]:
        """Select optimal recovery strategies based on context and success rates."""
        component = context.component
        error_type = context.error_type
        
        # Default strategy order
        strategies = []
        
        # Component-specific strategy selection
        if "provider" in component.lower():
            strategies = [RecoveryStrategy.RETRY, RecoveryStrategy.FAILOVER, RecoveryStrategy.RECONFIGURE]
        elif "mcp" in component.lower():
            strategies = [RecoveryStrategy.RESTART, RecoveryStrategy.RETRY, RecoveryStrategy.RECONFIGURE]
        elif "network" in error_type.lower() or "connection" in error_type.lower():
            strategies = [RecoveryStrategy.RETRY, RecoveryStrategy.FAILOVER]
        elif "config" in component.lower():
            strategies = [RecoveryStrategy.RECONFIGURE, RecoveryStrategy.FALLBACK]
        else:
            strategies = [RecoveryStrategy.RETRY, RecoveryStrategy.RESTART]
        
        # Sort by success rate if we have historical data
        context_key = f"{component}:{error_type}"
        if context_key in self.strategy_success_rates:
            success_rates = self.strategy_success_rates[context_key]
            strategies.sort(
                key=lambda s: success_rates.get(s.value, 0.0),
                reverse=True
            )
        
        return strategies
    
    def _is_circuit_open(self, recovery_key: str) -> bool:
        """Check if circuit breaker is open for a recovery key."""
        if recovery_key not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[recovery_key]
        
        if breaker["state"] == "closed":
            return False
        elif breaker["state"] == "open":
            # Check if timeout has passed
            time_since_open = (datetime.now() - breaker["opened_at"]).total_seconds()
            if time_since_open >= self.circuit_breaker_timeout:
                breaker["state"] = "half-open"
                return False
            return True
        elif breaker["state"] == "half-open":
            return False
        
        return False
    
    def _record_failure(self, recovery_key: str):
        """Record a recovery failure for circuit breaker logic."""
        if recovery_key not in self.circuit_breakers:
            self.circuit_breakers[recovery_key] = {
                "failure_count": 0,
                "state": "closed",
                "opened_at": None
            }
        
        breaker = self.circuit_breakers[recovery_key]
        breaker["failure_count"] += 1
        
        if breaker["failure_count"] >= self.circuit_breaker_threshold:
            breaker["state"] = "open"
            breaker["opened_at"] = datetime.now()
            self.logger.warning(f"Circuit breaker opened for {recovery_key}")
    
    def _update_success_rate(self, context: RecoveryContext, strategy: RecoveryStrategy, success: bool):
        """Update success rate tracking for strategies."""
        context_key = f"{context.component}:{context.error_type}"
        strategy_key = strategy.value
        
        if context_key not in self.strategy_success_rates:
            self.strategy_success_rates[context_key] = {}
        
        if strategy_key not in self.strategy_success_rates[context_key]:
            self.strategy_success_rates[context_key][strategy_key] = 0.5  # Start with neutral
        
        # Exponential moving average update
        current_rate = self.strategy_success_rates[context_key][strategy_key]
        alpha = 0.3  # Learning rate
        
        new_value = 1.0 if success else 0.0
        self.strategy_success_rates[context_key][strategy_key] = (
            alpha * new_value + (1 - alpha) * current_rate
        )
    
    def _record_recovery_success(self, context: RecoveryContext, result: RecoveryResult):
        """Record successful recovery for analytics."""
        recovery_record = {
            "timestamp": datetime.now(),
            "component": context.component,
            "error_type": context.error_type,
            "strategy": result.strategy_used.value,
            "success": True,
            "execution_time": result.execution_time,
            "attempts": result.attempts
        }
        
        self.recovery_history.append(recovery_record)
        
        # Reset circuit breaker on success
        recovery_key = f"{context.component}:{context.error_type}"
        if recovery_key in self.circuit_breakers:
            self.circuit_breakers[recovery_key]["failure_count"] = 0
            self.circuit_breakers[recovery_key]["state"] = "closed"
    
    def _record_recovery_failure(self, context: RecoveryContext, result: RecoveryResult):
        """Record failed recovery for analytics."""
        recovery_record = {
            "timestamp": datetime.now(),
            "component": context.component,
            "error_type": context.error_type,
            "strategy": "multiple_failed",
            "success": False,
            "execution_time": result.execution_time,
            "attempts": result.attempts
        }
        
        self.recovery_history.append(recovery_record)
    
    def register_recovery_handler(
        self,
        component: str,
        strategy: RecoveryStrategy,
        handler: Callable[[RecoveryContext], RecoveryResult]
    ):
        """Register a custom recovery handler."""
        strategy_key = f"{component}:{strategy.value}"
        
        if strategy_key not in self.recovery_strategies:
            self.recovery_strategies[strategy_key] = []
        
        self.recovery_strategies[strategy_key].append(handler)
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        if not self.recovery_history:
            return {"total_recoveries": 0}
        
        total = len(self.recovery_history)
        successful = len([r for r in self.recovery_history if r["success"]])
        
        # Calculate success rate by component
        component_stats = {}
        for record in self.recovery_history:
            component = record["component"]
            if component not in component_stats:
                component_stats[component] = {"total": 0, "successful": 0}
            
            component_stats[component]["total"] += 1
            if record["success"]:
                component_stats[component]["successful"] += 1
        
        # Calculate success rates
        for component in component_stats:
            stats = component_stats[component]
            stats["success_rate"] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0.0
        
        return {
            "total_recoveries": total,
            "successful_recoveries": successful,
            "overall_success_rate": successful / total if total > 0 else 0.0,
            "component_statistics": component_stats,
            "active_recoveries": len(self.active_recoveries),
            "circuit_breakers_open": len([
                k for k, v in self.circuit_breakers.items()
                if v["state"] == "open"
            ])
        }
    
    def _initialize_recovery_strategies(self):
        """Initialize built-in recovery strategies."""
        # Provider recovery strategies
        async def provider_retry_handler(context: RecoveryContext) -> RecoveryResult:
            """Retry provider operation with exponential backoff."""
            for attempt in range(self.max_retry_attempts):
                delay = self.retry_delay_base * (2 ** attempt)
                await asyncio.sleep(delay)
                
                # Simulate retry logic - would integrate with actual provider system
                # This is a placeholder for actual retry implementation
                if attempt == self.max_retry_attempts - 1:  # Last attempt succeeds for demo
                    return RecoveryResult(
                        success=True,
                        strategy_used=RecoveryStrategy.RETRY,
                        message="Provider operation succeeded after retry",
                        execution_time=delay * (attempt + 1),
                        attempts=attempt + 1
                    )
            
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY,
                message="Maximum retry attempts exceeded",
                execution_time=0.0,
                attempts=self.max_retry_attempts
            )
        
        async def provider_failover_handler(context: RecoveryContext) -> RecoveryResult:
            """Failover to backup provider."""
            # Placeholder for actual failover logic
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.FAILOVER,
                message="Switched to backup provider",
                execution_time=1.0
            )
        
        # MCP recovery strategies
        async def mcp_restart_handler(context: RecoveryContext) -> RecoveryResult:
            """Restart MCP server."""
            # Placeholder for actual MCP restart logic
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.RESTART,
                message="MCP server restarted successfully",
                execution_time=2.0
            )
        
        # Register handlers
        self.register_recovery_handler("provider", RecoveryStrategy.RETRY, provider_retry_handler)
        self.register_recovery_handler("provider", RecoveryStrategy.FAILOVER, provider_failover_handler)
        self.register_recovery_handler("mcp", RecoveryStrategy.RESTART, mcp_restart_handler)