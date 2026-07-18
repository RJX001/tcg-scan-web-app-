from __future__ import annotations

import httpx
import pytest
import respx
from structlog.testing import capture_logs

from tcgscan_agents.grade_roi_agent.graph import GradeROIInput, rules_node
from tcgscan_agents.tools.pricing import fetch_active_listings, fetch_comps_summary


@pytest.mark.asyncio
@respx.mock
async def test_fetch_comps_summary_non_200_logs_warning_and_returns_empty() -> None:
    card_id = "charizard-base"
    respx.get("http://localhost:8000/v1/cards/charizard-base/comps/summary").mock(
        return_value=httpx.Response(503)
    )

    with capture_logs() as cap:
        result = await fetch_comps_summary(card_id)

    assert result == {"card_id": card_id, "days": 30, "count": 0, "median_usd": None}
    warning = next(e for e in cap if e["event"] == "tool.pricing.comps_failed")
    assert warning["log_level"] == "warning"
    assert warning["card_id"] == card_id
    assert warning["status_code"] == 503


@pytest.mark.asyncio
@respx.mock
async def test_fetch_active_listings_non_200_logs_warning_and_returns_empty() -> None:
    card_id = "charizard-base"
    respx.get("http://localhost:8000/v1/cards/charizard-base/listings").mock(
        return_value=httpx.Response(404)
    )

    with capture_logs() as cap:
        result = await fetch_active_listings(card_id)

    assert result == []
    warning = next(e for e in cap if e["event"] == "tool.pricing.listings_failed")
    assert warning["log_level"] == "warning"
    assert warning["card_id"] == card_id
    assert warning["status_code"] == 404


@pytest.mark.asyncio
@respx.mock
async def test_fetch_comps_summary_http_error_logs_warning_and_reraises() -> None:
    card_id = "charizard-base"
    respx.get("http://localhost:8000/v1/cards/charizard-base/comps/summary").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    with capture_logs() as cap:
        with pytest.raises(httpx.ConnectError, match="connection refused"):
            await fetch_comps_summary(card_id)

    warning = next(e for e in cap if e["event"] == "tool.pricing.request_failed")
    assert warning["log_level"] == "warning"
    assert warning["card_id"] == card_id
    assert "connection refused" in warning["error"]


@respx.mock
def test_grade_roi_http_error_logs_warning_and_hold() -> None:
    card_id = "charizard-base"
    respx.get("http://localhost:8000/v1/cards/charizard-base/comps/summary").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    state = {"input": GradeROIInput(card_id=card_id), "output": None}

    with capture_logs() as cap:
        result = rules_node(state)

    assert result["output"] is not None
    assert result["output"].action == "HOLD"
    assert result["output"].reason == "Insufficient comps for ROI."
    warning = next(e for e in cap if e["event"] == "grade_roi.comps_fetch_failed")
    assert warning["log_level"] == "warning"
    assert "connection refused" in warning["error"]
