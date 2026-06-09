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


def test_parse_beckett_and_ace() -> None:
    bgs = parse_grade_from_text("Charizard BGS 9.5")
    assert bgs.grade_company == "BGS"
    assert bgs.grade == "BGS 9.5"

    beckett = parse_grade_from_text("Charizard Beckett 9")
    assert beckett.grade_company == "BGS"
    assert beckett.grade == "BGS 9"

    ace = parse_grade_from_text("Charizard ACE 10")
    assert ace.grade_company == "ACE"
    assert ace.grade == "ACE 10"
