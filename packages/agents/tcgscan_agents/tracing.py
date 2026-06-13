from __future__ import annotations

import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import structlog

P = ParamSpec("P")
R = TypeVar("R")

log = structlog.get_logger()


def traced(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            log.info("agent.node.start", node=name)
            try:
                return fn(*args, **kwargs)
            finally:
                log.info("agent.node.end", node=name)

        return wrapper

    return decorator
