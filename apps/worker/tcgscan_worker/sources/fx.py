"""Daily FX rates source (ECB reference rates via frankfurter.dev).

Free, keyless, ECB-backed. Rates update once per working day (~16:00 CET);
no published rate limit but one call per day is all we need — keep
`rate_per_sec` minimal. Results land in the `fx_rate` table
(rate_to_usd = value of 1 unit of currency in USD).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from tcgscan_worker.http import ResilientClient

log = structlog.get_logger()

BASE_URL = "https://api.frankfurter.dev/v1"

# Currencies we display; extend freely — ECB publishes ~30.
CURRENCIES = ("GBP", "EUR", "JPY", "CAD", "AUD", "CHF")


@dataclass
class FxSnapshot:
    day: datetime
    # currency -> value of 1 unit in USD
    rates_to_usd: dict[str, float]


class FxSource:
    def __init__(self, client: ResilientClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> ResilientClient:
        if self._client is None:
            self._client = ResilientClient(base_url=BASE_URL, rate_per_sec=0.1, burst=2)
        return self._client

    async def latest(self) -> FxSnapshot:
        payload = await self.client.get_json(
            "/latest", params={"base": "USD", "symbols": ",".join(CURRENCIES)}
        )
        # frankfurter returns units of currency per 1 USD; invert for rate_to_usd
        per_usd: dict[str, float] = payload.get("rates", {})
        rates_to_usd = {"USD": 1.0}
        for currency, units in per_usd.items():
            if units:
                rates_to_usd[currency.upper()] = 1.0 / float(units)
        day_str = payload.get("date")
        day = (
            datetime.fromisoformat(day_str).replace(tzinfo=timezone.utc)
            if isinstance(day_str, str)
            else datetime.now(timezone.utc)
        )
        log.info("fx.fetched", day=day.date().isoformat(), currencies=len(rates_to_usd))
        return FxSnapshot(day=day, rates_to_usd=rates_to_usd)
