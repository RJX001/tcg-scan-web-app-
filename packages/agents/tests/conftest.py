"""Keep structlog.testing.capture_logs working in the monorepo pytest process.

API ``configure_logging()`` switches structlog to stdlib BoundLogger with
``cache_logger_on_first_use=True``. Once those loggers have been used, later
``capture_logs()`` calls in packages/agents see an empty capture even though
JSON lines still hit stdout.
"""

from __future__ import annotations

import pytest
import structlog

from tcgscan_agents import budget as budget_mod
from tcgscan_agents import tracing as tracing_mod
from tcgscan_agents.grade_roi_agent import graph as grade_roi_graph_mod
from tcgscan_agents.tools import pricing as pricing_mod


@pytest.fixture(autouse=True)
def _capture_logs_compatible_structlog() -> None:
    structlog.reset_defaults()
    tracing_mod.log = structlog.get_logger(tracing_mod.__name__)
    budget_mod.log = structlog.get_logger(budget_mod.__name__)
    grade_roi_graph_mod.log = structlog.get_logger(grade_roi_graph_mod.__name__)
    pricing_mod.log = structlog.get_logger(pricing_mod.__name__)
    yield
