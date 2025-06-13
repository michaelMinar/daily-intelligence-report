"""
Tests for connector resilience features.
"""
import time
from unittest.mock import Mock, patch

import pytest

from src.connectors.exceptions import NetworkError, RateLimitError
from src.connectors.resilience import (
    network_retry,
    rate_limit_retry,
    CircuitBreaker,
    get_retry_after,
)


class TestRetryDecorators:
    """Tests for retry decorators."""
    
    def test_network_retry_succeeds_on_first_attempt(self):
        """Test function succeeds without retry."""
        mock_func = Mock(return_value="success")
        decorated = network_retry(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_network_retry_succeeds_after_failures(self):
        """Test function succeeds after network errors."""
        mock_func = Mock(side_effect=[
            NetworkError("Network error 1"),
            NetworkError("Network error 2"),
            "success"
        ])
        decorated = network_retry(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_network_retry_exhausts_attempts(self):
        """Test retry gives up after max attempts."""
        mock_func = Mock(side_effect=NetworkError("Network error"))
        decorated = network_retry(mock_func)
        
        # tenacity raises RetryError when attempts exhausted
        from tenacity import RetryError
        with pytest.raises(RetryError):
            decorated()
        
        # Should try 3 times (initial + 2 retries)
        assert mock_func.call_count == 3
    
    def test_network_retry_ignores_other_exceptions(self):
        """Test retry doesn't catch non-network errors."""
        mock_func = Mock(side_effect=ValueError("Not a network error"))
        decorated = network_retry(mock_func)
        
        with pytest.raises(ValueError):
            decorated()
        
        # Should not retry
        assert mock_func.call_count == 1
    
    def test_rate_limit_retry_respects_retry_after(self):
        """Test rate limit retry waits specified time."""
        # Mock time.sleep to avoid actual waiting
        with patch('tenacity.nap.time') as mock_nap:
            error = RateLimitError("Rate limited", retry_after=5)
            mock_func = Mock(side_effect=[error, "success"])
            decorated = rate_limit_retry(mock_func)
            
            result = decorated()
            
            assert result == "success"
            assert mock_func.call_count == 2
            # Should sleep for 5 seconds (from retry_after)
            mock_nap.sleep.assert_called_with(5)
    
    def test_get_retry_after_extracts_value(self):
        """Test get_retry_after extracts retry_after from exception."""
        # Create mock retry state with RateLimitError
        retry_state = Mock()
        retry_state.outcome = Mock(failed=True)
        retry_state.outcome.exception.return_value = RateLimitError("Error", retry_after=30)
        
        assert get_retry_after(retry_state) == 30
    
    def test_get_retry_after_defaults_to_60(self):
        """Test get_retry_after defaults when no retry_after."""
        # Create mock retry state without retry_after
        retry_state = Mock()
        retry_state.outcome = Mock(failed=True)
        retry_state.outcome.exception.return_value = RateLimitError("Error")
        
        assert get_retry_after(retry_state) == 60


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state allows calls."""
        cb = CircuitBreaker(failure_threshold=3)
        mock_func = Mock(return_value="success")
        
        result = cb.call(mock_func)
        
        assert result == "success"
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        mock_func = Mock(side_effect=Exception("Error"))
        
        # First 3 failures should pass through
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(mock_func)
        
        assert cb.state == CircuitBreaker.OPEN
        assert cb.failure_count == 3
        
        # Next call should fail immediately without calling function
        with pytest.raises(Exception) as exc_info:
            cb.call(mock_func)
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
        # Function should still have been called only 3 times
        assert mock_func.call_count == 3
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit breaker enters half-open state after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        mock_func = Mock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(mock_func)
        
        assert cb.state == CircuitBreaker.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Next call should attempt function (half-open state)
        with pytest.raises(Exception):
            cb.call(mock_func)
        
        # Function should have been called again
        assert mock_func.call_count == 3
    
    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets on successful call."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Add some failures
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(Mock(side_effect=Exception("Error")))
        
        assert cb.failure_count == 2
        
        # Successful call should reset
        result = cb.call(Mock(return_value="success"))
        
        assert result == "success"
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_decorator(self):
        """Test circuit breaker as decorator."""
        cb = CircuitBreaker(failure_threshold=2)
        
        @cb
        def test_func(value):
            if value == "error":
                raise Exception("Error")
            return value
        
        # Success calls
        assert test_func("hello") == "hello"
        
        # Trigger failures
        with pytest.raises(Exception):
            test_func("error")
        with pytest.raises(Exception):
            test_func("error")
        
        # Circuit should be open
        with pytest.raises(Exception) as exc_info:
            test_func("hello")
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    def test_circuit_breaker_only_catches_expected_exception(self):
        """Test circuit breaker only catches specified exception type."""
        cb = CircuitBreaker(expected_exception=NetworkError)
        
        # NetworkError should be caught and counted
        with pytest.raises(NetworkError):
            cb.call(Mock(side_effect=NetworkError("Network error")))
        
        assert cb.failure_count == 1
        
        # Other exceptions should pass through without counting
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("Other error")))
        
        assert cb.failure_count == 1  # Should not increment
    
    def test_circuit_breaker_manual_reset(self):
        """Test manual reset of circuit breaker."""
        cb = CircuitBreaker(failure_threshold=2)
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(Mock(side_effect=Exception("Error")))
        
        assert cb.state == CircuitBreaker.OPEN
        
        # Manual reset
        cb.reset()
        
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
    
    def test_circuit_breaker_properties(self):
        """Test circuit breaker state properties."""
        cb = CircuitBreaker()
        
        assert cb.is_closed
        assert not cb.is_open
        
        # Open the circuit
        for _ in range(5):  # Default threshold is 5
            with pytest.raises(Exception):
                cb.call(Mock(side_effect=Exception("Error")))
        
        assert not cb.is_closed
        assert cb.is_open