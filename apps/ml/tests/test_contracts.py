from pathlib import Path


def test_contracts_file_exists() -> None:
    p = Path(__file__).parent.parent / "contracts.md"
    assert p.read_text(encoding="utf-8").startswith("# ML")
