"""
Comprehensive deployment management system with multiple strategies and environment support.
"""

import asyncio
import json
import logging
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import tempfile
import hashlib

from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table


class DeploymentStrategy(Enum):
    """Deployment strategies."""
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling" 
    CANARY = "canary"
    RECREATE = "recreate"
    SHADOW = "shadow"
    A_B_TESTING = "ab_testing"


class DeploymentEnvironment(Enum):
    """Deployment environments."""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DeploymentStatus(Enum):
    """Deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"
    CANCELLED = "cancelled"


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    strategy: DeploymentStrategy
    environment: DeploymentEnvironment
    version: str
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    health_check_url: Optional[str] = None
    health_check_timeout: int = 30
    rollback_on_failure: bool = True
    notification_channels: List[str] = field(default_factory=list)
    pre_deploy_hooks: List[str] = field(default_factory=list)
    post_deploy_hooks: List[str] = field(default_factory=list)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    scaling_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    deployment_id: str
    status: DeploymentStatus
    strategy: DeploymentStrategy
    environment: DeploymentEnvironment
    version: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    rollback_performed: bool = False
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)


@dataclass
class DeploymentEnvironmentConfig:
    """Environment-specific configuration."""
    name: DeploymentEnvironment
    base_url: Optional[str] = None
    api_endpoints: Dict[str, str] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    scaling_config: Dict[str, Any] = field(default_factory=dict)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    health_checks: Dict[str, str] = field(default_factory=dict)
    monitoring_config: Dict[str, Any] = field(default_factory=dict)


class BaseDeploymentStrategy:
    """Base class for deployment strategies."""
    
    def __init__(self, strategy: DeploymentStrategy, logger: logging.Logger):
        self.strategy = strategy
        self.logger = logger
    
    async def deploy(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig) -> DeploymentResult:
        """Execute deployment with this strategy."""
        raise NotImplementedError
    
    async def rollback(self, deployment_id: str, env_config: DeploymentEnvironmentConfig) -> bool:
        """Rollback deployment."""
        raise NotImplementedError
    
    async def health_check(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig) -> bool:
        """Perform health check after deployment."""
        if not config.health_check_url:
            return True
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config.health_check_url,
                    timeout=aiohttp.ClientTimeout(total=config.health_check_timeout)
                ) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False


class BlueGreenDeployment(BaseDeploymentStrategy):
    """Blue-Green deployment strategy."""
    
    def __init__(self, logger: logging.Logger):
        super().__init__(DeploymentStrategy.BLUE_GREEN, logger)
    
    async def deploy(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig) -> DeploymentResult:
        """Execute blue-green deployment."""
        deployment_id = f"bg_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        result = DeploymentResult(
            deployment_id=deployment_id,
            status=DeploymentStatus.IN_PROGRESS,
            strategy=self.strategy,
            environment=config.environment,
            version=config.version,
            start_time=start_time
        )
        
        try:
            self.logger.info(f"Starting Blue-Green deployment {deployment_id}")
            result.logs.append("Blue-Green deployment started")
            
            # Step 1: Deploy to green environment
            result.logs.append("Deploying to green environment")
            await self._deploy_to_green(config, env_config)
            
            # Step 2: Health check green environment
            result.logs.append("Performing health check on green environment")
            if not await self.health_check(config, env_config):
                raise Exception("Health check failed on green environment")
            
            # Step 3: Switch traffic to green
            result.logs.append("Switching traffic to green environment")
            await self._switch_traffic_to_green(config, env_config)
            
            # Step 4: Verify traffic switch
            await asyncio.sleep(5)  # Allow time for traffic to switch
            result.logs.append("Verifying traffic switch")
            
            # Step 5: Clean up blue environment
            result.logs.append("Cleaning up blue environment")
            await self._cleanup_blue_environment(config, env_config)
            
            result.status = DeploymentStatus.SUCCESS
            result.success = True
            result.logs.append("Blue-Green deployment completed successfully")
            
        except Exception as e:
            self.logger.error(f"Blue-Green deployment failed: {e}")
            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            result.logs.append(f"Deployment failed: {e}")
            
            # Attempt rollback if enabled
            if config.rollback_on_failure:
                try:
                    result.logs.append("Attempting rollback")
                    await self.rollback(deployment_id, env_config)
                    result.rollback_performed = True
                    result.logs.append("Rollback completed")
                except Exception as rollback_error:
                    result.logs.append(f"Rollback failed: {rollback_error}")
        
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _deploy_to_green(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig):
        """Deploy application to green environment."""
        # Simulate deployment process
        await asyncio.sleep(2)
        self.logger.info("Application deployed to green environment")
    
    async def _switch_traffic_to_green(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig):
        """Switch traffic from blue to green environment."""
        # Simulate traffic switch
        await asyncio.sleep(1)
        self.logger.info("Traffic switched to green environment")
    
    async def _cleanup_blue_environment(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig):
        """Clean up blue environment after successful deployment."""
        # Simulate cleanup
        await asyncio.sleep(1)
        self.logger.info("Blue environment cleaned up")
    
    async def rollback(self, deployment_id: str, env_config: DeploymentEnvironmentConfig) -> bool:
        """Rollback blue-green deployment."""
        try:
            # Switch traffic back to blue
            await asyncio.sleep(1)
            self.logger.info(f"Rolled back deployment {deployment_id}")
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False


class RollingDeployment(BaseDeploymentStrategy):
    """Rolling deployment strategy."""
    
    def __init__(self, logger: logging.Logger):
        super().__init__(DeploymentStrategy.ROLLING, logger)
    
    async def deploy(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig) -> DeploymentResult:
        """Execute rolling deployment."""
        deployment_id = f"rolling_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        result = DeploymentResult(
            deployment_id=deployment_id,
            status=DeploymentStatus.IN_PROGRESS,
            strategy=self.strategy,
            environment=config.environment,
            version=config.version,
            start_time=start_time
        )
        
        try:
            self.logger.info(f"Starting Rolling deployment {deployment_id}")
            result.logs.append("Rolling deployment started")
            
            # Get current instance count
            instance_count = config.scaling_config.get('instances', 3)
            batch_size = config.scaling_config.get('batch_size', 1)
            
            # Deploy in batches
            for batch in range(0, instance_count, batch_size):
                batch_end = min(batch + batch_size, instance_count)
                result.logs.append(f"Deploying instances {batch+1}-{batch_end}")
                
                # Deploy batch
                await self._deploy_batch(batch, batch_end, config, env_config)
                
                # Health check batch
                if not await self._health_check_batch(batch, batch_end, config, env_config):
                    raise Exception(f"Health check failed for instances {batch+1}-{batch_end}")
                
                result.logs.append(f"Instances {batch+1}-{batch_end} deployed successfully")
                
                # Wait before next batch
                if batch_end < instance_count:
                    await asyncio.sleep(2)
            
            result.status = DeploymentStatus.SUCCESS
            result.success = True
            result.logs.append("Rolling deployment completed successfully")
            
        except Exception as e:
            self.logger.error(f"Rolling deployment failed: {e}")
            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            result.logs.append(f"Deployment failed: {e}")
        
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _deploy_batch(self, start_idx: int, end_idx: int, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig):
        """Deploy a batch of instances."""
        # Simulate batch deployment
        await asyncio.sleep(1.5)
        self.logger.info(f"Deployed instances {start_idx+1}-{end_idx}")
    
    async def _health_check_batch(self, start_idx: int, end_idx: int, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig) -> bool:
        """Health check a batch of instances."""
        # Simulate health check
        await asyncio.sleep(0.5)
        return True
    
    async def rollback(self, deployment_id: str, env_config: DeploymentEnvironmentConfig) -> bool:
        """Rollback rolling deployment."""
        try:
            # Roll back in reverse order
            await asyncio.sleep(2)
            self.logger.info(f"Rolled back deployment {deployment_id}")
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False


class CanaryDeployment(BaseDeploymentStrategy):
    """Canary deployment strategy."""
    
    def __init__(self, logger: logging.Logger):
        super().__init__(DeploymentStrategy.CANARY, logger)
    
    async def deploy(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig) -> DeploymentResult:
        """Execute canary deployment."""
        deployment_id = f"canary_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        result = DeploymentResult(
            deployment_id=deployment_id,
            status=DeploymentStatus.IN_PROGRESS,
            strategy=self.strategy,
            environment=config.environment,
            version=config.version,
            start_time=start_time
        )
        
        try:
            self.logger.info(f"Starting Canary deployment {deployment_id}")
            result.logs.append("Canary deployment started")
            
            # Step 1: Deploy canary instance (5% traffic)
            result.logs.append("Deploying canary instance (5% traffic)")
            await self._deploy_canary_instance(config, env_config, traffic_percent=5)
            
            # Step 2: Monitor canary for issues
            result.logs.append("Monitoring canary instance")
            if not await self._monitor_canary(config, env_config, duration=10):
                raise Exception("Canary monitoring detected issues")
            
            # Step 3: Increase canary traffic (25%)
            result.logs.append("Increasing canary traffic to 25%")
            await self._adjust_canary_traffic(config, env_config, traffic_percent=25)
            
            # Step 4: Monitor again
            if not await self._monitor_canary(config, env_config, duration=10):
                raise Exception("Canary monitoring detected issues at 25% traffic")
            
            # Step 5: Complete rollout (100%)
            result.logs.append("Completing canary rollout (100% traffic)")
            await self._complete_canary_rollout(config, env_config)
            
            result.status = DeploymentStatus.SUCCESS
            result.success = True
            result.logs.append("Canary deployment completed successfully")
            
        except Exception as e:
            self.logger.error(f"Canary deployment failed: {e}")
            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            result.logs.append(f"Deployment failed: {e}")
        
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _deploy_canary_instance(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig, traffic_percent: int):
        """Deploy canary instance with specified traffic percentage."""
        await asyncio.sleep(1)
        self.logger.info(f"Canary instance deployed with {traffic_percent}% traffic")
    
    async def _monitor_canary(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig, duration: int) -> bool:
        """Monitor canary instance for issues."""
        await asyncio.sleep(duration / 10)  # Simulate monitoring
        # In practice, this would check metrics, error rates, etc.
        return True
    
    async def _adjust_canary_traffic(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig, traffic_percent: int):
        """Adjust traffic percentage to canary instance."""
        await asyncio.sleep(0.5)
        self.logger.info(f"Canary traffic adjusted to {traffic_percent}%")
    
    async def _complete_canary_rollout(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig):
        """Complete the canary rollout."""
        await asyncio.sleep(1)
        self.logger.info("Canary rollout completed")
    
    async def rollback(self, deployment_id: str, env_config: DeploymentEnvironmentConfig) -> bool:
        """Rollback canary deployment."""
        try:
            # Route all traffic back to stable version
            await asyncio.sleep(1)
            self.logger.info(f"Rolled back canary deployment {deployment_id}")
            return True
        except Exception as e:
            self.logger.error(f"Canary rollback failed: {e}")
            return False


class DeploymentManager:
    """Main deployment manager that orchestrates all deployment strategies."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.deployment")
        
        # Strategy registry
        self.strategies: Dict[DeploymentStrategy, BaseDeploymentStrategy] = {
            DeploymentStrategy.BLUE_GREEN: BlueGreenDeployment(self.logger),
            DeploymentStrategy.ROLLING: RollingDeployment(self.logger),
            DeploymentStrategy.CANARY: CanaryDeployment(self.logger)
        }
        
        # Environment configurations
        self.environments: Dict[DeploymentEnvironment, DeploymentEnvironmentConfig] = {}
        
        # Deployment history
        self.deployment_history: List[DeploymentResult] = []
        
        # Active deployments
        self.active_deployments: Dict[str, DeploymentResult] = {}
        
        # Hooks
        self.pre_deploy_hooks: List[Callable] = []
        self.post_deploy_hooks: List[Callable] = []
        
        # Initialize default environments
        self._initialize_default_environments()
    
    def _initialize_default_environments(self):
        """Initialize default environment configurations."""
        # Local environment
        self.environments[DeploymentEnvironment.LOCAL] = DeploymentEnvironmentConfig(
            name=DeploymentEnvironment.LOCAL,
            base_url="http://localhost:8000",
            resource_limits={'cpu': '1', 'memory': '512Mi'},
            scaling_config={'instances': 1, 'batch_size': 1},
            environment_variables={'ENV': 'local'},
            health_checks={'http': '/health'}
        )
        
        # Development environment
        self.environments[DeploymentEnvironment.DEVELOPMENT] = DeploymentEnvironmentConfig(
            name=DeploymentEnvironment.DEVELOPMENT,
            base_url="https://dev.codexa.example.com",
            resource_limits={'cpu': '2', 'memory': '1Gi'},
            scaling_config={'instances': 2, 'batch_size': 1},
            environment_variables={'ENV': 'development'},
            health_checks={'http': '/health'}
        )
        
        # Staging environment
        self.environments[DeploymentEnvironment.STAGING] = DeploymentEnvironmentConfig(
            name=DeploymentEnvironment.STAGING,
            base_url="https://staging.codexa.example.com",
            resource_limits={'cpu': '4', 'memory': '2Gi'},
            scaling_config={'instances': 3, 'batch_size': 1},
            environment_variables={'ENV': 'staging'},
            health_checks={'http': '/health'}
        )
        
        # Production environment
        self.environments[DeploymentEnvironment.PRODUCTION] = DeploymentEnvironmentConfig(
            name=DeploymentEnvironment.PRODUCTION,
            base_url="https://codexa.example.com",
            resource_limits={'cpu': '8', 'memory': '4Gi'},
            scaling_config={'instances': 5, 'batch_size': 2},
            environment_variables={'ENV': 'production'},
            health_checks={'http': '/health', 'tcp': '8080'}
        )
    
    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """Execute deployment with specified configuration."""
        # Validate configuration
        if config.environment not in self.environments:
            raise ValueError(f"Environment {config.environment} not configured")
        
        if config.strategy not in self.strategies:
            raise ValueError(f"Strategy {config.strategy} not supported")
        
        env_config = self.environments[config.environment]
        strategy = self.strategies[config.strategy]
        
        self.console.print(f"[cyan]Starting {config.strategy.value} deployment to {config.environment.value}[/cyan]")
        
        # Execute pre-deploy hooks
        await self._execute_pre_deploy_hooks(config, env_config)
        
        # Execute deployment
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            
            deploy_task = progress.add_task(f"Deploying {config.version}", total=None)
            
            try:
                result = await strategy.deploy(config, env_config)
                
                # Track deployment
                self.deployment_history.append(result)
                if result.status == DeploymentStatus.IN_PROGRESS:
                    self.active_deployments[result.deployment_id] = result
                
                # Execute post-deploy hooks
                if result.success:
                    await self._execute_post_deploy_hooks(config, env_config, result)
                
                # Display result
                if result.success:
                    self.console.print(f"[green]✓ Deployment {result.deployment_id} completed successfully[/green]")
                else:
                    self.console.print(f"[red]✗ Deployment {result.deployment_id} failed: {result.error_message}[/red]")
                
                progress.update(deploy_task, completed=True)
                return result
                
            except Exception as e:
                self.logger.error(f"Deployment failed: {e}")
                self.console.print(f"[red]✗ Deployment failed: {e}[/red]")
                raise
    
    async def rollback(self, deployment_id: str) -> bool:
        """Rollback a specific deployment."""
        # Find deployment in history
        deployment = None
        for d in self.deployment_history:
            if d.deployment_id == deployment_id:
                deployment = d
                break
        
        if not deployment:
            self.console.print(f"[red]Deployment {deployment_id} not found[/red]")
            return False
        
        env_config = self.environments[deployment.environment]
        strategy = self.strategies[deployment.strategy]
        
        self.console.print(f"[yellow]Rolling back deployment {deployment_id}[/yellow]")
        
        try:
            success = await strategy.rollback(deployment_id, env_config)
            
            if success:
                deployment.status = DeploymentStatus.ROLLBACK
                self.console.print(f"[green]✓ Rollback completed for {deployment_id}[/green]")
            else:
                self.console.print(f"[red]✗ Rollback failed for {deployment_id}[/red]")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            self.console.print(f"[red]✗ Rollback failed: {e}[/red]")
            return False
    
    def add_environment(self, env_config: DeploymentEnvironmentConfig):
        """Add a new deployment environment."""
        self.environments[env_config.name] = env_config
        self.logger.info(f"Added environment: {env_config.name.value}")
    
    def add_pre_deploy_hook(self, hook: Callable):
        """Add a pre-deployment hook."""
        self.pre_deploy_hooks.append(hook)
    
    def add_post_deploy_hook(self, hook: Callable):
        """Add a post-deployment hook."""
        self.post_deploy_hooks.append(hook)
    
    async def _execute_pre_deploy_hooks(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig):
        """Execute pre-deployment hooks."""
        for hook in self.pre_deploy_hooks + config.pre_deploy_hooks:
            try:
                if callable(hook):
                    await hook(config, env_config)
                else:
                    # Execute shell command
                    await self._execute_shell_command(hook, config, env_config)
            except Exception as e:
                self.logger.error(f"Pre-deploy hook failed: {e}")
                raise
    
    async def _execute_post_deploy_hooks(self, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig, result: DeploymentResult):
        """Execute post-deployment hooks."""
        for hook in self.post_deploy_hooks + config.post_deploy_hooks:
            try:
                if callable(hook):
                    await hook(config, env_config, result)
                else:
                    # Execute shell command
                    await self._execute_shell_command(hook, config, env_config)
            except Exception as e:
                self.logger.warning(f"Post-deploy hook failed: {e}")
                # Don't fail deployment for post-deploy hook failures
    
    async def _execute_shell_command(self, command: str, config: DeploymentConfig, env_config: DeploymentEnvironmentConfig):
        """Execute shell command with environment variables."""
        env = {
            'DEPLOYMENT_ENVIRONMENT': config.environment.value,
            'DEPLOYMENT_VERSION': config.version,
            'DEPLOYMENT_STRATEGY': config.strategy.value
        }
        env.update(env_config.environment_variables)
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Command failed: {stderr.decode()}")
        
        self.logger.info(f"Command executed: {command}")
    
    def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentResult]:
        """Get status of a specific deployment."""
        for deployment in self.deployment_history:
            if deployment.deployment_id == deployment_id:
                return deployment
        return None
    
    def get_environment_deployments(self, environment: DeploymentEnvironment) -> List[DeploymentResult]:
        """Get all deployments for a specific environment."""
        return [d for d in self.deployment_history if d.environment == environment]
    
    def get_deployment_history(self, limit: int = 50) -> List[DeploymentResult]:
        """Get recent deployment history."""
        return self.deployment_history[-limit:]
    
    def get_active_deployments(self) -> Dict[str, DeploymentResult]:
        """Get currently active deployments."""
        return self.active_deployments.copy()
    
    def get_deployment_statistics(self) -> Dict[str, Any]:
        """Get deployment statistics."""
        total_deployments = len(self.deployment_history)
        successful_deployments = len([d for d in self.deployment_history if d.success])
        failed_deployments = len([d for d in self.deployment_history if not d.success])
        rollbacks = len([d for d in self.deployment_history if d.rollback_performed])
        
        # Calculate average deployment time
        completed_deployments = [d for d in self.deployment_history if d.duration is not None]
        avg_deployment_time = sum(d.duration for d in completed_deployments) / len(completed_deployments) if completed_deployments else 0
        
        # Strategy statistics
        strategy_stats = {}
        for strategy in DeploymentStrategy:
            strategy_deployments = [d for d in self.deployment_history if d.strategy == strategy]
            strategy_stats[strategy.value] = {
                'total': len(strategy_deployments),
                'successful': len([d for d in strategy_deployments if d.success]),
                'success_rate': len([d for d in strategy_deployments if d.success]) / len(strategy_deployments) if strategy_deployments else 0
            }
        
        return {
            'total_deployments': total_deployments,
            'successful_deployments': successful_deployments,
            'failed_deployments': failed_deployments,
            'success_rate': successful_deployments / total_deployments if total_deployments > 0 else 0,
            'rollbacks': rollbacks,
            'rollback_rate': rollbacks / total_deployments if total_deployments > 0 else 0,
            'average_deployment_time': avg_deployment_time,
            'active_deployments': len(self.active_deployments),
            'strategy_statistics': strategy_stats,
            'environments_configured': len(self.environments)
        }
    
    def display_deployment_summary(self):
        """Display deployment summary table."""
        stats = self.get_deployment_statistics()
        
        # Summary table
        table = Table(title="Deployment Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Deployments", str(stats['total_deployments']))
        table.add_row("Success Rate", f"{stats['success_rate']:.1%}")
        table.add_row("Rollback Rate", f"{stats['rollback_rate']:.1%}")
        table.add_row("Avg Deploy Time", f"{stats['average_deployment_time']:.1f}s")
        table.add_row("Active Deployments", str(stats['active_deployments']))
        
        self.console.print(table)
        
        # Recent deployments
        recent_deployments = self.get_deployment_history(10)
        if recent_deployments:
            self.console.print("\n[bold]Recent Deployments:[/bold]")
            
            recent_table = Table()
            recent_table.add_column("ID", style="dim")
            recent_table.add_column("Environment", style="cyan")
            recent_table.add_column("Strategy", style="yellow")
            recent_table.add_column("Status", style="green")
            recent_table.add_column("Duration")
            
            for deployment in recent_deployments[-5:]:  # Last 5
                status_style = "green" if deployment.success else "red"
                duration = f"{deployment.duration:.1f}s" if deployment.duration else "N/A"
                
                recent_table.add_row(
                    deployment.deployment_id[:12] + "...",
                    deployment.environment.value,
                    deployment.strategy.value,
                    f"[{status_style}]{deployment.status.value}[/{status_style}]",
                    duration
                )
            
            self.console.print(recent_table)