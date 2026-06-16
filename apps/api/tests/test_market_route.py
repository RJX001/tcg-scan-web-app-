from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tcgscan_api.db.models import CardPriceDaily, Game, MarketplaceListing, SaleKind
from tcgscan_api.db.session import get_session
from tcgscan_api.main import app, fastapi_app
from tcgscan_api.repositories.cards import CardsRepo
from tcgscan_api.repositories.market import MarketRepo, PopulationRepo
from tcgscan_api.repositories.sales import SalesRepo
from tcgscan_api.services.market import get_market_index


async def _seed_two_cards(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    cards = CardsRepo(session)
    await cards.upsert_many(
        [
            {"game": Game.pokemon, "name": "Charizard", "set_code": "base1", "number": "4/102"},
            {"game": Game.pokemon, "name": "Pikachu", "set_code": "base1", "number": "58/102"},
        ]
    )
    zard = await cards.get_by_external(Game.pokemon, "base1", "4/102")
    pika = await cards.get_by_external(Game.pokemon, "base1", "58/102")
    assert zard is not None and pika is not None

    now = datetime.now()

    def sale(card_id: uuid.UUID, days_ago: int, price: str, tag: str) -> dict[str, object]:
        return {
            "card_id": card_id,
            "source": "ebay",
            "kind": SaleKind.sold,
            "sold_at": now - timedelta(days=days_ago),
            "price": Decimal(price),
            "currency": "USD",
            "price_usd": Decimal(price),
            "grade": "raw",
            "listing_url": f"https://ebay.com/itm/{card_id}-{tag}",
        }

    rows: list[dict[str, object]] = []
    # Charizard: 100 -> 200 (+100%)
    rows += [sale(zard.id, 5, "200.00", "cur1"), sale(zard.id, 10, "200.00", "cur2")]
    rows += [sale(zard.id, 40, "100.00", "prev1"), sale(zard.id, 45, "100.00", "prev2")]
    # Pikachu: 10 -> 5 (-50%)
    rows += [sale(pika.id, 3, "5.00", "cur1"), sale(pika.id, 8, "5.00", "cur2")]
    rows += [sale(pika.id, 38, "10.00", "prev1"), sale(pika.id, 50, "10.00", "prev2")]
    await SalesRepo(session).bulk_insert(rows)
    return zard.id, pika.id


@pytest.mark.asyncio
async def test_market_repo_movers_change(sqlite_session: AsyncSession) -> None:
    zard_id, pika_id = await _seed_two_cards(sqlite_session)
    rows = await MarketRepo(sqlite_session).movers(days=30, sort="change")
    assert [r.card.id for r in rows] == [zard_id, pika_id]

    zard = rows[0]
    assert zard.sales_count == 2
    assert zard.change_pct is not None and abs(zard.change_pct - 100.0) < 0.01
    assert zard.last_sold_usd == 200.0
    assert zard.last_sold_at is not None

    pika = rows[1]
    assert pika.change_pct is not None and abs(pika.change_pct + 50.0) < 0.01


@pytest.mark.asyncio
async def test_market_repo_movers_filters_and_sorts(sqlite_session: AsyncSession) -> None:
    zard_id, pika_id = await _seed_two_cards(sqlite_session)
    repo = MarketRepo(sqlite_session)

    by_name = await repo.movers(q="pika")
    assert [r.card.id for r in by_name] == [pika_id]

    losers_first = await repo.movers(sort="change_asc")
    assert losers_first[0].card.id == pika_id

    by_price = await repo.movers(sort="price")
    assert by_price[0].card.id == zard_id

    assert await repo.movers(game="mtg") == []
    paged = await repo.movers(sort="change", limit=1, offset=1)
    assert [r.card.id for r in paged] == [pika_id]


@pytest.mark.asyncio
async def test_population_totals_and_endpoint(sqlite_session: AsyncSession) -> None:
    zard_id, _pika_id = await _seed_two_cards(sqlite_session)
    repo = PopulationRepo(sqlite_session)
    await repo.upsert_many(
        [
            {"card_id": zard_id, "grade_company": "PSA", "grade": "10", "pop_count": 100},
            {"card_id": zard_id, "grade_company": "PSA", "grade": "9", "pop_count": 250},
        ]
    )
    # Upsert overwrites existing counts
    await repo.upsert_many(
        [{"card_id": zard_id, "grade_company": "PSA", "grade": "10", "pop_count": 120}]
    )
    totals = await repo.totals_for_cards([zard_id])
    assert totals[zard_id] == 370

    movers = await MarketRepo(sqlite_session).movers(sort="change")
    assert movers[0].pop_count == 370
    assert movers[1].pop_count is None

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/v1/cards/{zard_id}/population")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 370
        assert {e["grade"]: e["pop_count"] for e in body["entries"]} == {"10": 120, "9": 250}
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_market_index(sqlite_session: AsyncSession) -> None:
    zard_id, pika_id = await _seed_two_cards(sqlite_session)
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Charizard +10%, Pikachu -10% over the window -> flat composite
    series = {zard_id: ("100", "110"), pika_id: ("10", "9")}
    for card_id, (early, late) in series.items():
        for days_ago, price in ((10, early), (2, late)):
            sqlite_session.add(
                CardPriceDaily(
                    card_id=card_id,
                    day=now - timedelta(days=days_ago),
                    grade_bucket="raw",
                    sample_count=1,
                    mean_usd=Decimal(price),
                    median_usd=Decimal(price),
                    min_usd=Decimal(price),
                    max_usd=Decimal(price),
                )
            )
    await sqlite_session.commit()

    out = await get_market_index(sqlite_session, days=30)
    assert len(out.points) == 2
    assert out.points[0].index_value == 100.0
    assert out.points[-1].index_value == 100.0  # +10% and -10% cancel out
    assert out.points[-1].constituents == 2
    assert out.change_pct == 0.0

    empty = await get_market_index(sqlite_session, game="mtg", days=30)
    assert empty.points == []

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/v1/market/index?days=30&game=pokemon")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Pokemon Index"
        assert len(body["points"]) >= 1
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_browse_listings(sqlite_session: AsyncSession) -> None:
    zard_id, pika_id = await _seed_two_cards(sqlite_session)
    now = datetime.now()
    listings: list[dict[str, object]] = [
        {
            "card_id": zard_id,
            "source": "ebay",
            "kind": SaleKind.listing,
            "sold_at": now,
            "price": Decimal("250.00"),
            "currency": "USD",
            "price_usd": Decimal("250.00"),
            "grade": "PSA 9",
            "listing_url": "https://ebay.com/itm/shop-1",
        },
        {
            "card_id": pika_id,
            "source": "tcgplayer",
            "kind": SaleKind.listing,
            "sold_at": now - timedelta(hours=1),
            "price": Decimal("6.00"),
            "currency": "USD",
            "price_usd": Decimal("6.00"),
            "grade": None,
            "listing_url": "https://tcgplayer.com/shop-2",
        },
    ]
    await SalesRepo(sqlite_session).bulk_insert(listings)
    repo = MarketRepo(sqlite_session)

    recent = await repo.browse_listings(sort="recent")
    assert [r.card.id for r in recent] == [zard_id, pika_id]

    cheap_first = await repo.browse_listings(sort="price_asc")
    assert cheap_first[0].card.id == pika_id

    only_ebay = await repo.browse_listings(source="ebay")
    assert len(only_ebay) == 1 and only_ebay[0].source == "ebay"

    raw_only = await repo.browse_listings(grade="raw")
    assert len(raw_only) == 1 and raw_only[0].card.id == pika_id

    in_range = await repo.browse_listings(min_price=100, max_price=300)
    assert len(in_range) == 1 and in_range[0].card.id == zard_id

    by_name = await repo.browse_listings(q="pika")
    assert len(by_name) == 1 and by_name[0].card.id == pika_id

    sqlite_session.add_all(
        [
            MarketplaceListing(
                source="ebay",
                source_listing_id="shop-zard",
                title="Charizard shop listing",
                price=Decimal("250.00"),
                currency="USD",
                item_url="https://ebay.com/itm/shop-1",
                grade="PSA 9",
                card_id=zard_id,
                listing_status="active",
            ),
            MarketplaceListing(
                source="tcgplayer",
                source_listing_id="shop-pika",
                title="Pikachu shop listing",
                price=Decimal("6.00"),
                currency="USD",
                item_url="https://tcgplayer.com/shop-2",
                card_id=pika_id,
                listing_status="active",
            ),
        ]
    )
    await sqlite_session.commit()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/v1/market/listings?sort=price_desc&limit=10")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        assert body[0]["card"]["name"] == "Charizard"
        assert body[0]["price_usd"] == 250.0
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_movers_grade_filter(sqlite_session: AsyncSession) -> None:
    zard_id, pika_id = await _seed_two_cards(sqlite_session)
    now = datetime.now()
    graded_sales: list[dict[str, object]] = [
        {
            "card_id": zard_id,
            "source": "ebay",
            "kind": SaleKind.sold,
            "sold_at": now - timedelta(days=1),
            "price": Decimal("900.00"),
            "currency": "USD",
            "price_usd": Decimal("900.00"),
            "grade": "PSA 10",
            "listing_url": "https://ebay.com/itm/psa10",
        },
        {
            "card_id": zard_id,
            "source": "ebay",
            "kind": SaleKind.sold,
            "sold_at": now - timedelta(days=2),
            "price": Decimal("400.00"),
            "currency": "USD",
            "price_usd": Decimal("400.00"),
            "grade": "BGS 9.5",
            "listing_url": "https://ebay.com/itm/bgs95",
        },
    ]
    await SalesRepo(sqlite_session).bulk_insert(graded_sales)
    repo = MarketRepo(sqlite_session)

    psa_only = await repo.movers(grade="PSA")
    assert len(psa_only) == 1
    assert psa_only[0].card.id == zard_id
    assert psa_only[0].last_sold_grade == "PSA 10"

    graded = await repo.movers(grade="graded")
    assert len(graded) == 1 and graded[0].sales_count == 2

    raw_only = await repo.movers(grade="raw")
    # seeded base sales are raw, so both cards still rank
    assert {r.card.id for r in raw_only} == {zard_id, pika_id}
    assert all(r.last_sold_grade is None or r.last_sold_grade.lower() == "raw" for r in raw_only)

    sgc_only = await repo.movers(grade="SGC")
    assert sgc_only == []


@pytest.mark.asyncio
async def test_pop_and_market_cap_sorts(sqlite_session: AsyncSession) -> None:
    zard_id, pika_id = await _seed_two_cards(sqlite_session)
    await PopulationRepo(sqlite_session).upsert_many(
        [
            {"card_id": pika_id, "grade_company": "PSA", "grade": "10", "pop_count": 9000},
            {"card_id": zard_id, "grade_company": "PSA", "grade": "10", "pop_count": 100},
        ]
    )
    repo = MarketRepo(sqlite_session)
    by_pop = await repo.movers(sort="pop")
    assert [r.card.id for r in by_pop] == [pika_id, zard_id]

    # market cap: zard 200*100=20k beats pika 5*9000=45k -> pika first
    by_cap = await repo.movers(sort="market_cap")
    assert by_cap[0].card.id == pika_id


@pytest.mark.asyncio
async def test_pop_sort_requires_pro(sqlite_session: AsyncSession) -> None:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # free tier dev user -> 403 (dev auth resolves anonymous to a free user too)
            r = await client.get(
                "/v1/market/movers?sort=pop", headers={"X-Dev-User-Id": "free-user"}
            )
            assert r.status_code == 403
            r = await client.get("/v1/market/movers?sort=pop")
            assert r.status_code == 403
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_indexes_summary(sqlite_session: AsyncSession) -> None:
    zard_id, _pika_id = await _seed_two_cards(sqlite_session)
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for days_ago, price in ((6, "100"), (1, "110")):
        sqlite_session.add(
            CardPriceDaily(
                card_id=zard_id,
                day=now - timedelta(days=days_ago),
                grade_bucket="raw",
                sample_count=1,
                mean_usd=Decimal(price),
                median_usd=Decimal(price),
                min_usd=Decimal(price),
                max_usd=Decimal(price),
            )
        )
    await sqlite_session.commit()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/v1/market/indexes?days=7")
        assert r.status_code == 200
        body = r.json()
        keys = {i["key"] for i in body}
        assert "all" in keys and "pokemon" in keys
        pokemon = next(i for i in body if i["key"] == "pokemon")
        assert pokemon["change_pct"] == 10.0
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_browse_sales(sqlite_session: AsyncSession) -> None:
    zard_id, _pika_id = await _seed_two_cards(sqlite_session)
    repo = MarketRepo(sqlite_session)

    all_sales = await repo.browse_sales(sort="recent")
    assert len(all_sales) >= 2

    psa_only = await repo.browse_sales(grade="PSA")
    assert all(s.grade is None or s.grade.upper().startswith("PSA") for s in psa_only)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/v1/market/sales?limit=5&grade=raw")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        if body:
            assert "sold_at" in body[0] and "market_region" in body[0]
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_fx_rates(sqlite_session: AsyncSession) -> None:
    from tcgscan_api.repositories.fx import FxRepo

    repo = FxRepo(sqlite_session)
    old_day = datetime(2026, 1, 1)
    new_day = datetime(2026, 6, 1)
    await repo.upsert_many(day=old_day, rates_to_usd={"GBP": 1.20, "EUR": 1.05})
    await repo.upsert_many(day=new_day, rates_to_usd={"GBP": 1.27})

    as_of, rates = await repo.latest_rates()
    assert as_of == new_day
    assert rates["GBP"] == 1.27  # newest day wins
    assert rates["EUR"] == 1.05  # older day still served until refreshed

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/v1/market/fx")
        assert r.status_code == 200
        body = r.json()
        assert body["base"] == "USD"
        assert body["rates"]["GBP"] == 1.27
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_market_movers_route(sqlite_session: AsyncSession) -> None:
    await _seed_two_cards(sqlite_session)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    fastapi_app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/v1/market/movers?game=pokemon&sort=change&limit=20")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        top = body[0]
        assert top["card"]["name"] == "Charizard"
        assert top["sales_count"] == 2
        assert round(top["change_pct"]) == 100
        assert top["last_sold_usd"] == 200.0
    finally:
        fastapi_app.dependency_overrides.clear()
