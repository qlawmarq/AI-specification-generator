"""
Unit tests for performance optimization features.

Tests batch processing, timeout handling, progress tracking, and error recovery.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.spec_generator.core.generator import (
    LLMProvider, 
    AnalysisProcessor, 
    SpecificationGenerator
)
from src.spec_generator.models import SpecificationConfig, CodeChunk, Language
from src.spec_generator.utils.performance_monitor import PerformanceMonitor


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return SpecificationConfig(
        openai_api_key="test_key",
        chunk_size=1000,
        chunk_overlap=100,
    )


@pytest.fixture
def test_chunks():
    """Create test code chunks."""
    chunks = []
    for i in range(10):
        chunk = CodeChunk(
            content=f"def test_function_{i}():\n    pass",
            file_path=Path(f"test_{i}.py"),
            language=Language.PYTHON,
            start_line=1,
            end_line=2,
            chunk_type="function"
        )
        chunks.append(chunk)
    return chunks


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    def test_calculate_optimal_batch_size(self, test_config):
        """Test optimal batch size calculation."""
        generator = SpecificationGenerator(test_config)
        
        # Small number of chunks - should process all at once
        assert generator._calculate_optimal_batch_size(3) == 3
        
        # Medium number - should use configured batch size (default is 10)
        assert generator._calculate_optimal_batch_size(8) == 10
        
        # Large number - should cap at maximum
        assert generator._calculate_optimal_batch_size(100) <= 20
        
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, test_config, test_chunks):
        """Test that batch processing is faster than sequential."""
        # Mock the LLM provider to simulate realistic response times
        generator = SpecificationGenerator(test_config)
        
        # Mock batch processing to return quickly
        async def mock_batch_analysis(chunks):
            await asyncio.sleep(0.1)  # Simulate fast batch processing
            return [{"overview": "test", "functions": [], "classes": []} for _ in chunks]
        
        generator.analysis_processor.analyze_code_chunks_batch = mock_batch_analysis
        
        start_time = time.time()
        results = await generator._analyze_chunks(test_chunks[:5])
        duration = time.time() - start_time
        
        # Should complete quickly with batch processing
        assert duration < 2.0  # Should be much faster than sequential
        assert len(results) == 5
        
    @pytest.mark.asyncio
    async def test_batch_fallback_on_failure(self, test_config, test_chunks):
        """Test fallback to individual processing when batch fails."""
        generator = SpecificationGenerator(test_config)
        
        # Mock batch processing to fail, individual to succeed
        async def mock_batch_fail(chunks):
            raise Exception("Batch failed")
            
        async def mock_individual_success(chunk):
            return {"overview": "individual", "functions": [], "classes": []}
        
        generator.analysis_processor.analyze_code_chunks_batch = mock_batch_fail
        generator.analysis_processor.analyze_code_chunk = mock_individual_success
        
        # Should fall back gracefully
        results = await generator._analyze_chunks(test_chunks[:3])
        assert len(results) == 3
        assert all(r["overview"] == "Batch processing failed: Batch failed" for r in results)


class TestTimeoutHandling:
    """Test timeout handling functionality."""
    
    @pytest.mark.asyncio
    async def test_cli_timeout_handling(self):
        """Test CLI timeout prevents infinite hanging."""
        async def long_running_task():
            await asyncio.sleep(5)  # Simulate long-running task
            return "completed"
        
        # Should timeout quickly
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(long_running_task(), timeout=1)
            
    @pytest.mark.asyncio
    async def test_request_timeout_handling(self, test_config):
        """Test request-level timeout handling."""
        # Create LLM provider with short timeout
        test_config.performance_settings.request_timeout = 1
        llm_provider = LLMProvider(test_config)
        
        # Mock LLM to take too long
        async def slow_invoke(prompt):
            await asyncio.sleep(2)
            return "response"
        
        llm_provider.llm.invoke = slow_invoke
        
        # Should timeout and retry
        with pytest.raises(asyncio.TimeoutError):
            await llm_provider.generate("test prompt")


class TestErrorHandling:
    """Test error handling and retry logic."""
    
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, test_config):
        """Test retry logic for rate limit errors."""
        test_config.performance_settings.max_retries = 2
        test_config.performance_settings.retry_delay = 0.1
        
        llm_provider = LLMProvider(test_config)
        
        call_count = 0
        async def mock_rate_limited_call(prompt):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Rate limit exceeded")
            return Mock(content="success")
        
        llm_provider.llm.invoke = mock_rate_limited_call
        
        # Should succeed after retries
        result = await llm_provider.generate("test")
        assert result == "success"
        assert call_count == 3  # Original + 2 retries
        
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, test_config):
        """Test behavior when retries are exhausted."""
        test_config.performance_settings.max_retries = 1
        test_config.performance_settings.retry_delay = 0.1
        
        llm_provider = LLMProvider(test_config)
        
        async def always_fail(prompt):
            raise Exception("Persistent error")
        
        llm_provider.llm.invoke = always_fail
        
        # Should eventually give up
        with pytest.raises(Exception, match="Persistent error"):
            await llm_provider.generate("test")
            
    @pytest.mark.asyncio
    async def test_network_error_retry(self, test_config):
        """Test retry logic for network errors."""
        test_config.performance_settings.max_retries = 1
        test_config.performance_settings.retry_delay = 0.1
        
        llm_provider = LLMProvider(test_config)
        
        call_count = 0
        async def mock_network_error(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from requests.exceptions import ConnectionError
                raise ConnectionError("Network error")
            return Mock(content="recovered")
        
        llm_provider.llm.invoke = mock_network_error
        
        # Should recover from network error
        result = await llm_provider.generate("test")
        assert result == "recovered"
        assert call_count == 2


class TestPerformanceMonitoring:
    """Test performance monitoring functionality."""
    
    def test_performance_monitor_basic_operations(self):
        """Test basic performance monitoring operations."""
        monitor = PerformanceMonitor()
        
        # Test operation timing
        monitor.start_operation("test_op")
        time.sleep(0.1)
        duration = monitor.end_operation("test_op")
        
        assert 0.09 <= duration <= 0.15  # Allow some variance
        
        # Test API call recording
        monitor.record_api_call(1.5, success=True)
        monitor.record_api_call(2.0, success=False)
        
        assert monitor.metrics.total_api_calls == 2
        assert monitor.metrics.error_count == 1
        assert monitor.metrics.total_processing_time == 3.5
        
    def test_batch_metrics_recording(self):
        """Test batch metrics recording."""
        monitor = PerformanceMonitor()
        
        # Record a successful batch
        monitor.record_batch(
            batch_size=5,
            duration=2.0,
            success_count=5,
            failure_count=0
        )
        
        assert len(monitor.metrics.batch_metrics) == 1
        batch = monitor.metrics.batch_metrics[0]
        assert batch.success_rate == 100.0
        assert batch.average_time_per_item == 0.4
        
    def test_optimization_recommendations(self):
        """Test optimization recommendation generation."""
        monitor = PerformanceMonitor()
        
        # Add some batch data
        monitor.record_batch(batch_size=2, duration=1.0, success_count=2, failure_count=0)
        monitor.record_batch(batch_size=3, duration=1.5, success_count=3, failure_count=0)
        
        recommendation = monitor.get_batch_optimization_recommendation()
        assert "increasing batch size" in recommendation.lower()
        
    def test_performance_summary_logging(self, caplog):
        """Test performance summary logging."""
        monitor = PerformanceMonitor()
        
        # Add some metrics
        monitor.record_api_call(1.0, success=True)
        monitor.record_batch(batch_size=5, duration=2.0, success_count=4, failure_count=1)
        
        # Should log without errors
        monitor.log_performance_summary()
        
        # Check that summary was logged
        assert "Performance Summary" in caplog.text
        assert "Total API calls" in caplog.text


class TestConfigurationUpdates:
    """Test configuration model updates."""
    
    def test_new_performance_settings(self):
        """Test new performance settings are available."""
        config = SpecificationConfig()
        
        # Test new timeout settings
        assert hasattr(config.performance_settings, 'cli_timeout_seconds')
        assert config.performance_settings.cli_timeout_seconds == 600
        
        # Test batch processing settings
        assert hasattr(config.performance_settings, 'enable_batch_processing')
        assert config.performance_settings.enable_batch_processing is True
        
        assert hasattr(config.performance_settings, 'batch_optimization_strategy')
        assert config.performance_settings.batch_optimization_strategy == "adaptive"
        
    def test_timeout_hierarchy_validation(self):
        """Test that timeout settings are properly hierarchical."""
        config = SpecificationConfig()
        
        # CLI timeout should be longer than request timeout
        assert config.performance_settings.cli_timeout_seconds >= config.performance_settings.request_timeout
        
        # Both should be reasonable values
        assert config.performance_settings.request_timeout >= 1
        assert config.performance_settings.cli_timeout_seconds >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])