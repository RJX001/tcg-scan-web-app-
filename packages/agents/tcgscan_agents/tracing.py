from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import structlog

P = ParamSpec("P")
R = TypeVar("R")

log = structlog.get_logger(__name__)


def traced(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            log.debug("agent.node.start", node=name)
            started = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                log.error(
                    "agent.node.failed",
                    node=name,
                    duration_ms=duration_ms,
                    exc_type=type(exc).__name__,
                )
                raise
            duration_ms = (time.perf_counter() - started) * 1000
            log.debug(
                "agent.node.end",
                node=name,
                duration_ms=duration_ms,
                status="ok",
            )
            return result

        return wrapper

    return decorator
