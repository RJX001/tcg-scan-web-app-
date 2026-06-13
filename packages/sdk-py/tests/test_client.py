from tcgscan_sdk.client import HealthResponse


def test_health_model() -> None:
    h = HealthResponse(status="ok", version="0.0.0")
    assert h.status == "ok"
