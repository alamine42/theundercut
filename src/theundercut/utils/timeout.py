"""Timeout utilities for wrapping blocking calls."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import wraps
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default timeout for FastF1 operations (seconds)
FASTF1_TIMEOUT = 45


class TimeoutError(Exception):
    """Raised when an operation times out."""

    def __init__(self, message: str, timeout: float):
        super().__init__(message)
        self.timeout = timeout


def run_with_timeout(
    func: Callable[[], T],
    timeout: float = FASTF1_TIMEOUT,
    description: str = "operation",
) -> T:
    """
    Run a callable with a timeout.

    Uses ThreadPoolExecutor to run the function in a separate thread
    and enforces a timeout. If the timeout is exceeded, raises TimeoutError.

    Note: The underlying thread may continue running after timeout,
    but control returns to the caller immediately.

    Args:
        func: Zero-argument callable to execute
        timeout: Maximum seconds to wait
        description: Human-readable description for error messages

    Returns:
        The result of func()

    Raises:
        TimeoutError: If the operation exceeds the timeout
        Exception: Any exception raised by func()
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.warning(
                "Timeout after %.1fs waiting for %s",
                timeout,
                description,
            )
            raise TimeoutError(
                f"{description} timed out after {timeout}s",
                timeout=timeout,
            )


def with_timeout(
    timeout: float = FASTF1_TIMEOUT,
    description: str | None = None,
):
    """
    Decorator to add timeout protection to a method.

    Args:
        timeout: Maximum seconds to wait
        description: Human-readable description (defaults to function name)

    Example:
        @with_timeout(30, "loading FastF1 session")
        def load_session(self):
            session.load()
            return session
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            desc = description or func.__name__
            return run_with_timeout(
                lambda: func(*args, **kwargs),
                timeout=timeout,
                description=desc,
            )

        return wrapper

    return decorator
