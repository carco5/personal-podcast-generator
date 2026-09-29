from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

VALID_SETTINGS = {
    "show_name": "Blaugrana Brief",
    "length_minutes": 7,
    "tone": "analytical",
    "hosts": [
        {"role": "host", "name": "Jordi", "personality": "Calm and precise."},
        {"role": "analyst", "name": "Laia", "personality": "Bold opinions, backed by numbers."},
    ],
    "schedule_days": [5, 1, 1],
    "schedule_time": "06:30",
    "timezone": "America/New_York",
}


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_catalog_lists_the_topics(client: TestClient) -> None:
    topics = client.get("/api/v1/catalog").json()

    keys = {topic["key"] for topic in topics}
    assert {"fc-barcelona-football", "fc-barcelona-basketball", "euroleague", "nba"} <= keys
    assert {topic["kind"] for topic in topics} == {"team", "competition"}
    assert {topic["sport"] for topic in topics} == {"football", "basketball"}


def test_default_settings(client: TestClient) -> None:
    settings = client.get("/api/v1/settings").json()

    assert settings["length_minutes"] == 5
    assert [host["role"] for host in settings["hosts"]] == ["host", "analyst"]
    assert settings["timezone"] == "Europe/Madrid"


def test_update_settings(client: TestClient) -> None:
    response = client.put("/api/v1/settings", json=VALID_SETTINGS)

    assert response.status_code == 200
    saved = client.get("/api/v1/settings").json()
    assert saved["show_name"] == "Blaugrana Brief"
    assert saved["hosts"][1]["name"] == "Laia"
    assert saved["schedule_days"] == [1, 5]
    assert saved["schedule_time"] == "06:30:00"


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("length_minutes", 10),
        ("tone", "funny"),
        ("hosts", VALID_SETTINGS["hosts"] * 2),
        ("hosts", VALID_SETTINGS["hosts"][::-1]),
        ("timezone", "Mars/Olympus"),
        ("schedule_days", [1, 8]),
        ("show_name", "   "),
    ],
)
def test_invalid_settings_are_rejected(client: TestClient, field: str, bad_value: object) -> None:
    body = deepcopy(VALID_SETTINGS)
    body[field] = bad_value

    response = client.put("/api/v1/settings", json=body)

    assert response.status_code == 422
    assert client.get("/api/v1/settings").json()["show_name"] == "Barça & Beyond"
