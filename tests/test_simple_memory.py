"""
Unit tests for spec_generator.utils.simple_memory module.

Tests for SimpleMemoryTracker functionality.
"""

import gc
from unittest.mock import Mock, patch

import pytest

from spec_generator.utils.simple_memory import SimpleMemoryTracker


class TestSimpleMemoryTracker:
    """Test SimpleMemoryTracker functionality."""

    def test_initialization(self):
        """Test SimpleMemoryTracker initialization."""
        tracker = SimpleMemoryTracker(max_memory_mb=512)

        assert tracker.max_memory_mb == 512
        assert tracker.peak_usage_mb == 0.0
        assert tracker.process is not None

    def test_initialization_with_defaults(self):
        """Test SimpleMemoryTracker initialization with default values."""
        tracker = SimpleMemoryTracker()

        assert tracker.max_memory_mb == 1024  # Default value
        assert tracker.peak_usage_mb == 0.0

    def test_get_current_usage_mb(self):
        """Test getting current memory usage."""
        tracker = SimpleMemoryTracker()

        usage = tracker.get_current_usage_mb()

        assert isinstance(usage, float)
        assert usage >= 0.0

        # Should update peak usage
        assert tracker.peak_usage_mb >= usage

    def test_get_current_usage_mb_with_error(self):
        """Test memory usage when psutil raises an error."""
        tracker = SimpleMemoryTracker()

        with patch.object(
            tracker.process, "memory_info", side_effect=Exception("Memory error")
        ):
            usage = tracker.get_current_usage_mb()

            # Should return 0.0 on error
            assert usage == 0.0

    def test_peak_usage_tracking(self):
        """Test peak usage tracking."""
        tracker = SimpleMemoryTracker()

        # Mock memory info to return increasing values
        with patch.object(tracker.process, "memory_info") as mock_memory_info:
            # First call returns 100MB
            mock_memory_info.return_value = Mock(rss=100 * 1024 * 1024)
            usage1 = tracker.get_current_usage_mb()
            assert usage1 == 100.0
            assert tracker.peak_usage_mb == 100.0

            # Second call returns 150MB
            mock_memory_info.return_value = Mock(rss=150 * 1024 * 1024)
            usage2 = tracker.get_current_usage_mb()
            assert usage2 == 150.0
            assert tracker.peak_usage_mb == 150.0

            # Third call returns 120MB (lower than peak)
            mock_memory_info.return_value = Mock(rss=120 * 1024 * 1024)
            usage3 = tracker.get_current_usage_mb()
            assert usage3 == 120.0
            assert tracker.peak_usage_mb == 150.0  # Peak should remain

    def test_should_trigger_gc_below_threshold(self):
        """Test GC triggering when below threshold."""
        tracker = SimpleMemoryTracker(max_memory_mb=1000)

        # Mock memory usage to be below 80% threshold
        with patch.object(tracker, "get_current_usage_mb", return_value=700.0):
            assert tracker.should_trigger_gc() is False

    def test_should_trigger_gc_above_threshold(self):
        """Test GC triggering when above threshold."""
        tracker = SimpleMemoryTracker(max_memory_mb=1000)

        # Mock memory usage to be above 80% threshold (800MB)
        with patch.object(tracker, "get_current_usage_mb", return_value=850.0):
            assert tracker.should_trigger_gc() is True

    def test_should_trigger_gc_at_threshold(self):
        """Test GC triggering exactly at threshold."""
        tracker = SimpleMemoryTracker(max_memory_mb=1000)

        # Mock memory usage to be exactly at 80% threshold
        with patch.object(tracker, "get_current_usage_mb", return_value=800.0):
            assert tracker.should_trigger_gc() is False

    def test_should_trigger_gc_just_above_threshold(self):
        """Test GC triggering just above threshold."""
        tracker = SimpleMemoryTracker(max_memory_mb=1000)

        # Mock memory usage to be just above 80% threshold
        with patch.object(tracker, "get_current_usage_mb", return_value=800.1):
            assert tracker.should_trigger_gc() is True

    def test_trigger_gc(self):
        """Test garbage collection triggering."""
        tracker = SimpleMemoryTracker()

        # Mock memory usage before and after GC
        with patch.object(tracker, "get_current_usage_mb", side_effect=[500.0, 400.0]):
            with patch("gc.collect", return_value=42) as mock_gc:
                stats = tracker.trigger_gc()

                mock_gc.assert_called_once()

                assert stats["usage_before_mb"] == 500.0
                assert stats["usage_after_mb"] == 400.0
                assert stats["memory_freed_mb"] == 100.0
                assert stats["objects_collected"] == 42

    def test_trigger_gc_no_memory_freed(self):
        """Test garbage collection when no memory is freed."""
        tracker = SimpleMemoryTracker()

        # Mock memory usage to be same before and after GC
        with patch.object(tracker, "get_current_usage_mb", return_value=500.0):
            with patch("gc.collect", return_value=0) as mock_gc:
                stats = tracker.trigger_gc()

                mock_gc.assert_called_once()

                assert stats["usage_before_mb"] == 500.0
                assert stats["usage_after_mb"] == 500.0
                assert stats["memory_freed_mb"] == 0.0
                assert stats["objects_collected"] == 0

    def test_get_peak_usage_mb(self):
        """Test getting peak memory usage."""
        tracker = SimpleMemoryTracker()

        # Initially should be 0
        assert tracker.get_peak_usage_mb() == 0.0

        # Mock memory usage to trigger peak tracking
        with patch.object(tracker.process, "memory_info") as mock_memory_info:
            mock_memory_info.return_value = Mock(rss=200 * 1024 * 1024)
            tracker.get_current_usage_mb()

            assert tracker.get_peak_usage_mb() == 200.0

    def test_get_memory_stats(self):
        """Test getting memory statistics."""
        tracker = SimpleMemoryTracker(max_memory_mb=1024)

        # Mock process memory info
        with patch.object(tracker.process, "memory_info") as mock_memory_info:
            with patch.object(tracker.process, "memory_percent") as mock_memory_percent:
                mock_memory_info.return_value = Mock(rss=512 * 1024 * 1024)
                mock_memory_percent.return_value = 25.0

                # Set peak usage
                tracker.peak_usage_mb = 600.0

                stats = tracker.get_memory_stats()

                assert stats["current_usage_mb"] == 512.0
                assert stats["current_usage_percent"] == 25.0
                assert stats["peak_usage_mb"] == 600.0
                assert stats["max_allowed_mb"] == 1024
                assert stats["usage_ratio"] == 0.5  # 512/1024

    def test_get_memory_stats_with_error(self):
        """Test memory stats when error occurs."""
        tracker = SimpleMemoryTracker()

        # Mock process to raise an exception
        with patch.object(
            tracker.process, "memory_info", side_effect=Exception("Memory error")
        ):
            stats = tracker.get_memory_stats()

            assert "error" in stats
            assert stats["error"] == "Memory error"

    def test_memory_tracking_integration(self):
        """Test complete memory tracking workflow."""
        tracker = SimpleMemoryTracker(max_memory_mb=500)

        # Simulate increasing memory usage
        with patch.object(tracker.process, "memory_info") as mock_memory_info:
            # Start with low memory
            mock_memory_info.return_value = Mock(rss=100 * 1024 * 1024)
            assert tracker.should_trigger_gc() is False

            # Increase to medium memory
            mock_memory_info.return_value = Mock(rss=300 * 1024 * 1024)
            assert tracker.should_trigger_gc() is False

            # Increase to high memory (above 80% of 500MB = 400MB)
            mock_memory_info.return_value = Mock(rss=450 * 1024 * 1024)
            assert tracker.should_trigger_gc() is True

            # Trigger GC
            with patch("gc.collect", return_value=10):
                # Mock memory reduction after GC
                with patch.object(
                    tracker, "get_current_usage_mb", side_effect=[450.0, 350.0]
                ):
                    stats = tracker.trigger_gc()

                    assert stats["memory_freed_mb"] == 100.0
                    assert stats["objects_collected"] == 10

    def test_memory_conversion_accuracy(self):
        """Test memory conversion from bytes to MB."""
        tracker = SimpleMemoryTracker()

        # Test various memory values
        test_cases = [
            (1024 * 1024, 1.0),  # 1MB
            (512 * 1024 * 1024, 512.0),  # 512MB
            (1536 * 1024 * 1024, 1536.0),  # 1.5GB
        ]

        for bytes_value, expected_mb in test_cases:
            with patch.object(tracker.process, "memory_info") as mock_memory_info:
                mock_memory_info.return_value = Mock(rss=bytes_value)
                usage = tracker.get_current_usage_mb()

                assert usage == expected_mb

    def test_threshold_calculation(self):
        """Test threshold calculation for different memory limits."""
        test_cases = [
            (100, 80.0),  # 80% of 100MB
            (1024, 819.2),  # 80% of 1024MB
            (2048, 1638.4),  # 80% of 2048MB
        ]

        for max_memory, expected_threshold in test_cases:
            tracker = SimpleMemoryTracker(max_memory_mb=max_memory)

            # Mock memory usage just below threshold
            with patch.object(
                tracker, "get_current_usage_mb", return_value=expected_threshold - 0.1
            ):
                assert tracker.should_trigger_gc() is False

            # Mock memory usage just above threshold
            with patch.object(
                tracker, "get_current_usage_mb", return_value=expected_threshold + 0.1
            ):
                assert tracker.should_trigger_gc() is True


# Integration tests
class TestMemoryTrackerIntegration:
    """Integration tests for SimpleMemoryTracker."""

    def test_real_memory_usage(self):
        """Test with real memory usage (no mocking)."""
        tracker = SimpleMemoryTracker(max_memory_mb=8192)  # 8GB limit

        # Get real memory usage
        usage = tracker.get_current_usage_mb()

        assert usage > 0.0
        assert isinstance(usage, float)
        assert tracker.peak_usage_mb >= usage

        # Should not trigger GC with high limit
        assert tracker.should_trigger_gc() is False

        # Get real memory stats
        stats = tracker.get_memory_stats()

        assert "current_usage_mb" in stats
        assert "peak_usage_mb" in stats
        assert "max_allowed_mb" in stats
        assert "usage_ratio" in stats
        assert stats["max_allowed_mb"] == 8192

    def test_gc_execution(self):
        """Test actual garbage collection execution."""
        tracker = SimpleMemoryTracker()

        # Trigger real GC
        stats = tracker.trigger_gc()

        assert "usage_before_mb" in stats
        assert "usage_after_mb" in stats
        assert "memory_freed_mb" in stats
        assert "objects_collected" in stats

        # All values should be numeric
        assert isinstance(stats["usage_before_mb"], float)
        assert isinstance(stats["usage_after_mb"], float)
        assert isinstance(stats["memory_freed_mb"], float)
        assert isinstance(stats["objects_collected"], int)


# Fixtures
@pytest.fixture
def memory_tracker():
    """Create a memory tracker for testing."""
    return SimpleMemoryTracker(max_memory_mb=1024)


@pytest.fixture
def high_memory_tracker():
    """Create a memory tracker with high memory limit."""
    return SimpleMemoryTracker(max_memory_mb=8192)


def test_memory_tracker_with_fixture(memory_tracker):
    """Test using memory tracker fixture."""
    assert memory_tracker.max_memory_mb == 1024
    assert memory_tracker.peak_usage_mb == 0.0

    # Test basic functionality
    usage = memory_tracker.get_current_usage_mb()
    assert usage >= 0.0


def test_high_memory_tracker_with_fixture(high_memory_tracker):
    """Test using high memory tracker fixture."""
    assert high_memory_tracker.max_memory_mb == 8192

    # Should not trigger GC with high limit
    assert high_memory_tracker.should_trigger_gc() is False
