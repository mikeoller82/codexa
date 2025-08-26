"""
Performance optimization and scaling improvements for Codexa.
"""

from .performance_optimizer import (
    PerformanceOptimizer,
    OptimizationStrategy,
    OptimizationResult,
    PerformanceMetric
)
from .cache_manager import (
    CacheManager,
    CacheStrategy,
    CacheEntry,
    CacheStatistics
)
from .resource_manager import (
    ResourceManager,
    ResourceType,
    ResourceLimit,
    ResourceUsage
)
from .scaling_manager import (
    ScalingManager,
    ScalingPolicy,
    ScalingMetric,
    ScalingAction
)
from .connection_pooling import (
    ConnectionPoolManager,
    ConnectionPool,
    PoolConfiguration,
    PoolStatistics
)

__all__ = [
    "PerformanceOptimizer",
    "OptimizationStrategy",
    "OptimizationResult",
    "PerformanceMetric",
    "CacheManager",
    "CacheStrategy",
    "CacheEntry",
    "CacheStatistics",
    "ResourceManager",
    "ResourceType",
    "ResourceLimit",
    "ResourceUsage",
    "ScalingManager",
    "ScalingPolicy",
    "ScalingMetric",
    "ScalingAction",
    "ConnectionPoolManager",
    "ConnectionPool",
    "PoolConfiguration",
    "PoolStatistics"
]