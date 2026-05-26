import pytest

from tcgscan_worker.sources.grade_parse import parse_grade_from_text


def test_parse_psa_grade() -> None:
    parsed = parse_grade_from_text("Charizard PSA 10 Gem Mint")
    assert parsed.grade_company == "PSA"
    assert parsed.grade == "PSA 10"


def test_parse_raw_default() -> None:
    parsed = parse_grade_from_text("Near Mint Holo Rare")
    assert parsed.grade == "raw"
    assert parsed.grade_company is None
