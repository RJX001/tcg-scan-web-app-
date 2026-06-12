"""PSA Population Report source.

PSA Public API: https://api.psacard.com/publicapi (token via `PSA_API_TOKEN`).
Rate limit: PSA allows 100 calls/day on the free tier — keep `rate_per_sec`
very low and run via the weekly `catalog_refresh`-style schedule, popular
cards first. Results land in the `card_population` table via the API repo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from tcgscan_worker.http import ResilientClient

log = structlog.get_logger()

BASE_URL = "https://api.psacard.com/publicapi"


@dataclass
class PopulationRecord:
    """Normalised population entry, maps 1:1 to the `card_population` table."""

    grade_company: str
    grade: str
    pop_count: int
    as_of: datetime
    raw_payload: dict[str, Any]

    def to_row(self) -> dict[str, Any]:
        return {
            "grade_company": self.grade_company,
            "grade": self.grade,
            "pop_count": self.pop_count,
            "as_of": self.as_of,
        }


class PsaPopSource:
    """Fetch PSA population by spec ID (PSA's card identifier).

    Spec IDs are resolved per card via `/spec/search` and should be cached in
    `card_identity.external_ids['psa_spec_id']` to conserve the daily quota.
    """

    def __init__(self, client: ResilientClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> ResilientClient:
        if self._client is None:
            token = os.getenv("PSA_API_TOKEN", "")
            self._client = ResilientClient(
                base_url=BASE_URL,
                rate_per_sec=0.02,  # ~100 calls/day free tier — stay well under
                burst=2,
                headers={"Authorization": f"Bearer {token}"},
            )
        return self._client

    async def find_spec_id(self, *, query: str) -> int | None:
        payload = await self.client.get_json("/spec/search", params={"query": query, "limit": 1})
        items = payload.get("specs") or payload.get("data") or []
        if not items:
            return None
        spec_id = items[0].get("specId") or items[0].get("SpecID")
        return int(spec_id) if spec_id is not None else None

    async def population_for_spec(self, spec_id: int) -> list[PopulationRecord]:
        payload = await self.client.get_json(f"/pop/GetPSASpecPopulation/{spec_id}")
        now = datetime.now(timezone.utc)
        records: list[PopulationRecord] = []
        entries = payload.get("PSASpecPopulationModel") or payload.get("data") or []
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            for grade_num in range(1, 11):
                count = entry.get(f"Grade{grade_num}") or entry.get(f"grade{grade_num}")
                if count is None:
                    continue
                records.append(
                    PopulationRecord(
                        grade_company="PSA",
                        grade=str(grade_num),
                        pop_count=int(count),
                        as_of=now,
                        raw_payload=entry,
                    )
                )
        log.info("psa_pop.fetched", spec_id=spec_id, grades=len(records))
        return records
