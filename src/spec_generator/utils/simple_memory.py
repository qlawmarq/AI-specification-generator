"""
Simple memory management utilities for the Japanese Specification Generator.

This module provides basic memory monitoring without complex threading or caching.
"""

import gc
import logging

import psutil

logger = logging.getLogger(__name__)


class SimpleMemoryTracker:
    """Simple memory tracker with basic threshold checking."""

    def __init__(self, max_memory_mb: int = 1024):
        """
        Initialize the memory tracker.
        Args:
            max_memory_mb: Maximum memory usage in MB before triggering cleanup.
        """
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        self.peak_usage_mb = 0.0

        logger.info(f"SimpleMemoryTracker initialized with {max_memory_mb}MB limit")

    def get_current_usage_mb(self) -> float:
        """
        Get current memory usage in MB.
        Returns:
            Current memory usage in MB.
        """
        try:
            memory_info = self.process.memory_info()
            usage_mb = memory_info.rss / (1024 * 1024)

            # Update peak usage
            if usage_mb > self.peak_usage_mb:
                self.peak_usage_mb = usage_mb

            return usage_mb
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return 0.0

    def should_trigger_gc(self) -> bool:
        """
        Check if garbage collection should be triggered.
        Returns:
            True if memory usage exceeds 80% of maximum.
        """
        current_mb = self.get_current_usage_mb()
        threshold = self.max_memory_mb * 0.8

        if current_mb > threshold:
            logger.warning(
                f"Memory usage high: {current_mb:.1f}MB / {self.max_memory_mb}MB "
                f"({current_mb/self.max_memory_mb:.1%})"
            )
            return True

        return False

    def trigger_gc(self) -> dict[str, float]:
        """
        Trigger garbage collection and return basic statistics.
        Returns:
            Dictionary with basic GC statistics.
        """
        usage_before = self.get_current_usage_mb()

        # Trigger garbage collection
        collected = gc.collect()

        usage_after = self.get_current_usage_mb()
        memory_freed = usage_before - usage_after

        stats = {
            "usage_before_mb": usage_before,
            "usage_after_mb": usage_after,
            "memory_freed_mb": memory_freed,
            "objects_collected": collected,
        }

        logger.debug(f"GC triggered: {stats}")
        return stats

    def get_peak_usage_mb(self) -> float:
        """
        Get peak memory usage in MB.
        Returns:
            Peak memory usage in MB.
        """
        return self.peak_usage_mb

    def get_memory_stats(self) -> dict[str, float]:
        """
        Get basic memory statistics.
        Returns:
            Dictionary with memory statistics.
        """
        try:
            current_usage = self.get_current_usage_mb()
            memory_percent = self.process.memory_percent()

            return {
                "current_usage_mb": current_usage,
                "current_usage_percent": memory_percent,
                "peak_usage_mb": self.peak_usage_mb,
                "max_allowed_mb": self.max_memory_mb,
                "usage_ratio": current_usage / self.max_memory_mb if self.max_memory_mb > 0 else 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}
