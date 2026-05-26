"""Grade-ladder ROI verdict — HOLD / SELL / GRADE from comps + condition."""

from __future__ import annotations

import statistics
import uuid
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.repositories.sales import SalesRepo

DEFAULT_GRADING_COST_USD = 25.0
MIN_GRADE_PROFIT_USD = 40.0


class GradeVerdict(BaseModel):
    action: Literal["HOLD", "SELL", "GRADE", "BUY"]
    reason: str
    raw_median_usd: float | None = None
    graded_estimate_usd: float | None = None
    expected_profit_usd: float | None = None
    grading_cost_usd: float = DEFAULT_GRADING_COST_USD


def _median(prices: list[float]) -> float | None:
    if not prices:
        return None
    return float(statistics.median(prices))


def _bucket_price(rows: Sequence[object], *, raw: bool, grade_prefix: str | None = None) -> float | None:
    prices: list[float] = []
    for r in rows:
        grade = getattr(r, "grade", None) or "raw"
        g = str(grade).upper()
        price = float(getattr(r, "price_usd") or getattr(r, "price"))
        if raw and g in {"RAW", "NONE", ""}:
            prices.append(price)
        elif grade_prefix and grade_prefix in g:
            prices.append(price)
    return _median(prices)


async def compute_verdict(
    session: AsyncSession,
    card_id: uuid.UUID,
    *,
    psa_high: int | None,
    days: int = 30,
) -> GradeVerdict | None:
    if psa_high is None:
        return None

    rows = await SalesRepo(session).comps_for_card(card_id, days=days)
    if not rows:
        return None

    raw_med = _bucket_price(rows, raw=True)
    psa10 = _bucket_price(rows, raw=False, grade_prefix="PSA 10")
    psa9 = _bucket_price(rows, raw=False, grade_prefix="PSA 9")

    graded_est = psa10 or psa9
    if graded_est is None and raw_med is not None and psa_high >= 9:
        graded_est = raw_med * 2.5
    if raw_med is None:
        return GradeVerdict(
            action="HOLD",
            reason="Not enough raw comps to estimate ROI — add more sales data.",
        )

    profit = None
    if graded_est is not None:
        profit = graded_est - raw_med - DEFAULT_GRADING_COST_USD

    if psa_high >= 9 and profit is not None and profit >= MIN_GRADE_PROFIT_USD:
        return GradeVerdict(
            action="GRADE",
            reason=(
                f"Estimated PSA {psa_high}+ grade could net "
                f"${profit:.0f} after ~${DEFAULT_GRADING_COST_USD:.0f} grading fees."
            ),
            raw_median_usd=raw_med,
            graded_estimate_usd=graded_est,
            expected_profit_usd=profit,
        )

    if psa_high <= 7:
        return GradeVerdict(
            action="SELL",
            reason="Condition likely tops out below PSA 8 — sell raw rather than grading.",
            raw_median_usd=raw_med,
            graded_estimate_usd=graded_est,
            expected_profit_usd=profit,
        )

    if profit is not None and profit < 0:
        return GradeVerdict(
            action="HOLD",
            reason="Grading fees likely exceed upside at this condition — hold raw.",
            raw_median_usd=raw_med,
            graded_estimate_usd=graded_est,
            expected_profit_usd=profit,
        )

    return GradeVerdict(
        action="HOLD",
        reason="Borderline grade candidate — monitor comps or improve centering before submitting.",
        raw_median_usd=raw_med,
        graded_estimate_usd=graded_est,
        expected_profit_usd=profit,
    )
