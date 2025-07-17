"""
Performance monitoring utilities for the Specification Generator.

This module provides tools for tracking API call efficiency, response times,
and batch processing optimization.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class BatchMetrics:
    """Metrics for a batch processing operation."""

    batch_size: int
    duration_seconds: float
    success_count: int
    failure_count: int
    average_time_per_item: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0.0


@dataclass
class PerformanceMetrics:
    """Overall performance metrics for specification generation."""

    total_api_calls: int = 0
    total_processing_time: float = 0.0
    batch_metrics: List[BatchMetrics] = field(default_factory=list)
    error_count: int = 0
    retry_count: int = 0

    @property
    def average_api_call_time(self) -> float:
        """Average time per API call."""
        return (self.total_processing_time / self.total_api_calls) if self.total_api_calls > 0 else 0.0

    @property
    def overall_success_rate(self) -> float:
        """Overall success rate across all operations."""
        total_operations = self.total_api_calls
        successful_operations = total_operations - self.error_count
        return (successful_operations / total_operations * 100) if total_operations > 0 else 0.0


class PerformanceMonitor:
    """Monitor and track performance metrics for optimization."""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.start_times: Dict[str, float] = {}

    def start_operation(self, operation_id: str) -> None:
        """Start timing an operation."""
        self.start_times[operation_id] = time.time()

    def end_operation(self, operation_id: str) -> float:
        """End timing an operation and return duration."""
        if operation_id not in self.start_times:
            logger.warning(f"Operation {operation_id} was not started")
            return 0.0

        duration = time.time() - self.start_times.pop(operation_id)
        return duration

    def record_api_call(self, duration: float, success: bool = True) -> None:
        """Record metrics for an API call."""
        self.metrics.total_api_calls += 1
        self.metrics.total_processing_time += duration

        if not success:
            self.metrics.error_count += 1

    def record_retry(self) -> None:
        """Record a retry operation."""
        self.metrics.retry_count += 1

    def record_batch(self, batch_size: int, duration: float, success_count: int, failure_count: int) -> None:
        """Record metrics for a batch operation."""
        avg_time = duration / batch_size if batch_size > 0 else 0.0

        batch_metrics = BatchMetrics(
            batch_size=batch_size,
            duration_seconds=duration,
            success_count=success_count,
            failure_count=failure_count,
            average_time_per_item=avg_time
        )

        self.metrics.batch_metrics.append(batch_metrics)

        # Also record individual API calls
        for _ in range(success_count):
            self.record_api_call(avg_time, success=True)
        for _ in range(failure_count):
            self.record_api_call(avg_time, success=False)

    def get_batch_optimization_recommendation(self) -> str:
        """Analyze batch metrics and provide optimization recommendations."""
        if not self.metrics.batch_metrics:
            return "No batch data available for analysis"

        recent_batches = self.metrics.batch_metrics[-5:]  # Last 5 batches

        # Calculate average metrics
        avg_batch_size = sum(b.batch_size for b in recent_batches) / len(recent_batches)
        avg_success_rate = sum(b.success_rate for b in recent_batches) / len(recent_batches)
        avg_time_per_item = sum(b.average_time_per_item for b in recent_batches) / len(recent_batches)

        recommendations = []

        # Batch size recommendations
        if avg_batch_size < 5 and avg_success_rate > 95:
            recommendations.append("Consider increasing batch size for better throughput")
        elif avg_batch_size > 15 and avg_success_rate < 80:
            recommendations.append("Consider reducing batch size to improve reliability")

        # Performance recommendations
        if avg_time_per_item > 10:
            recommendations.append("High processing time detected - check network latency and API limits")
        elif avg_time_per_item < 2:
            recommendations.append("Excellent performance - current configuration is optimal")

        # Error rate recommendations
        if avg_success_rate < 90:
            recommendations.append("High error rate detected - implement more aggressive retry logic")

        return " | ".join(recommendations) if recommendations else "Current performance is acceptable"

    def log_performance_summary(self) -> None:
        """Log a comprehensive performance summary."""
        logger.info("=== Performance Summary ===")
        logger.info(f"Total API calls: {self.metrics.total_api_calls}")
        logger.info(f"Total processing time: {self.metrics.total_processing_time:.2f}s")
        logger.info(f"Average call time: {self.metrics.average_api_call_time:.2f}s")
        logger.info(f"Success rate: {self.metrics.overall_success_rate:.1f}%")
        logger.info(f"Error count: {self.metrics.error_count}")
        logger.info(f"Retry count: {self.metrics.retry_count}")

        if self.metrics.batch_metrics:
            logger.info(f"Batch operations: {len(self.metrics.batch_metrics)}")
            total_items = sum(b.batch_size for b in self.metrics.batch_metrics)
            total_batch_time = sum(b.duration_seconds for b in self.metrics.batch_metrics)
            logger.info(f"Total items processed: {total_items}")
            logger.info(f"Average batch efficiency: {total_items/total_batch_time:.1f} items/second")

        recommendation = self.get_batch_optimization_recommendation()
        logger.info(f"Optimization recommendation: {recommendation}")
        logger.info("=== End Performance Summary ===")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
