"""Tests for timeout utilities."""
import time

import pytest

from theundercut.utils.timeout import (
    TimeoutError,
    run_with_timeout,
    with_timeout,
)


def test_run_with_timeout_success():
    """Function completing within timeout returns result."""

    def quick_func():
        return 42

    result = run_with_timeout(quick_func, timeout=5, description="quick test")
    assert result == 42


def test_run_with_timeout_exceeds():
    """Function exceeding timeout raises TimeoutError."""

    def slow_func():
        time.sleep(10)
        return "never returned"

    with pytest.raises(TimeoutError) as exc_info:
        run_with_timeout(slow_func, timeout=0.1, description="slow test")

    assert exc_info.value.timeout == 0.1
    assert "slow test" in str(exc_info.value)
    assert "timed out" in str(exc_info.value)


def test_run_with_timeout_propagates_exception():
    """Exceptions from the function are propagated."""

    def failing_func():
        raise ValueError("expected error")

    with pytest.raises(ValueError, match="expected error"):
        run_with_timeout(failing_func, timeout=5, description="failing test")


def test_with_timeout_decorator_success():
    """Decorator allows function to complete."""

    @with_timeout(5, "decorated test")
    def quick_method(x, y):
        return x + y

    result = quick_method(3, 4)
    assert result == 7


def test_with_timeout_decorator_exceeds():
    """Decorator raises TimeoutError on timeout."""

    @with_timeout(0.1, "slow decorated")
    def slow_method():
        time.sleep(10)
        return "never"

    with pytest.raises(TimeoutError) as exc_info:
        slow_method()

    assert "slow decorated" in str(exc_info.value)


def test_with_timeout_decorator_default_description():
    """Decorator uses function name as default description."""

    @with_timeout(0.1)
    def my_slow_function():
        time.sleep(10)

    with pytest.raises(TimeoutError) as exc_info:
        my_slow_function()

    assert "my_slow_function" in str(exc_info.value)
