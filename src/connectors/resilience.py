"""
Resilience patterns for connectors including retry logic and circuit breakers.
"""
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.connectors.exceptions import NetworkError, RateLimitError

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


def get_retry_after(retry_state: RetryCallState) -> int:
    """Extract retry_after value from RateLimitError."""
    if retry_state.outcome and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        if isinstance(exception, RateLimitError) and exception.retry_after:
            return exception.retry_after
    return 60  # Default to 60 seconds


# Network retry decorator - exponential backoff for network errors
network_retry = retry(
    retry=retry_if_exception_type(NetworkError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=lambda retry_state: logger.warning(
        f"Network error, retrying in {retry_state.next_action.sleep} seconds..."
    )
)


class WaitForRateLimit:
    """Custom wait strategy that respects rate limit retry-after values."""
    
    def __call__(self, retry_state: RetryCallState) -> float:
        """Return the number of seconds to wait based on retry-after header."""
        return float(get_retry_after(retry_state))


# Rate limit retry decorator - respects retry-after header
def rate_limit_retry(func: F) -> F:
    """Retry decorator that respects rate limit retry-after values."""
    return retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(2),  # Try once more after rate limit
        wait=WaitForRateLimit(),
        before_sleep=lambda retry_state: logger.info(
            f"Rate limited, waiting {get_retry_after(retry_state)} seconds..."
        )
    )(func)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch (others pass through)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = self.CLOSED
        
    def __call__(self, func: F) -> F:
        """Decorator to protect function calls with circuit breaker."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(lambda: func(*args, **kwargs))
        return cast(F, wrapper)
    
    def call(self, func: Callable[[], Any]) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == self.OPEN:
            if self._should_attempt_reset():
                self.state = self.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN (failures: {self.failure_count})")
        
        try:
            result = func()
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self) -> None:
        """Reset failure count on success."""
        self.failure_count = 0
        self.state = self.CLOSED
    
    def _on_failure(self) -> None:
        """Increment failure count and possibly open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout} seconds."
            )
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.CLOSED
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is in closed state."""
        return self.state == self.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is in open state."""
        return self.state == self.OPEN