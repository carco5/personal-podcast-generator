import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("method", "path", "codes"),
    [
        ("get", "/api/v1/health", {"200", "503"}),
        ("post", "/api/v1/interests", {"201", "409", "422"}),
        ("delete", "/api/v1/interests/{interest_id}", {"204", "404"}),
        ("get", "/api/v1/episodes/{episode_id}", {"200", "404"}),
        ("post", "/api/v1/episodes", {"202", "409", "503"}),
        ("post", "/api/v1/episodes/{episode_id}/retry", {"202", "404", "409", "503"}),
    ],
)
def test_error_responses_are_documented(
    client: TestClient, method: str, path: str, codes: set[str]
) -> None:
    documented = set(client.get("/openapi.json").json()["paths"][path][method]["responses"])

    assert codes <= documented
