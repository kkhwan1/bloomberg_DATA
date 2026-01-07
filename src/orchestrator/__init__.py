"""
Orchestrator Module

Workflow coordination, scheduling, and pipeline management.

Components:
    - CacheManager: SQLite-based cache with TTL and statistics
    - CostTracker: Budget and cost tracking
    - CircuitBreaker: Fault tolerance and resilience pattern
    - HybridDataSource: Priority-based multi-source data retrieval
    - DataScheduler: APScheduler-based periodic data collection
    - CrawlOrchestrator: Main orchestrator for crawl workflows
    - TaskScheduler: Scheduling and timing of crawl tasks
    - PipelineManager: Manages data processing pipeline stages
    - WorkflowConfig: Configuration for workflow execution
    - ErrorRecovery: Error handling and recovery strategies
"""

__all__ = [
    "CacheManager",
    "CostTracker",
    "CircuitBreaker",
    "HybridDataSource",
    "DataScheduler",
    "CrawlOrchestrator",
    "TaskScheduler",
    "PipelineManager",
    "WorkflowConfig",
    "ErrorRecovery",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "CacheManager":
        from .cache_manager import CacheManager
        return CacheManager
    elif name == "CostTracker":
        from .cost_tracker import CostTracker
        return CostTracker
    elif name == "CircuitBreaker":
        from .circuit_breaker import CircuitBreaker
        return CircuitBreaker
    elif name == "HybridDataSource":
        from .hybrid_source import HybridDataSource
        return HybridDataSource
    elif name == "DataScheduler":
        from .scheduler import DataScheduler
        return DataScheduler
    elif name in __all__:
        # Import will be added when actual classes are implemented
        raise ImportError(f"{name} not yet implemented")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
