from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import api_router
from app.main import add_frontend

BROWSER = {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
FETCH = {"Accept": "application/json"}


def app_with_frontend(tmp_path: Path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id='root'></div>")
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    application = FastAPI()
    application.include_router(api_router)
    add_frontend(application, tmp_path)
    return TestClient(application)


def test_every_screen_loads_directly_and_on_refresh(tmp_path: Path) -> None:
    client = app_with_frontend(tmp_path)

    for path in ("/", "/settings", "/internal"):
        response = client.get(path, headers=BROWSER)
        assert response.status_code == 200 and "id='root'" in response.text, path
    assert client.get("/assets/app.js").text == "console.log('app')"


def test_the_api_is_never_answered_with_the_page(tmp_path: Path) -> None:
    client = app_with_frontend(tmp_path)

    assert client.get("/api/v1/health", headers=BROWSER).json() == {"status": "ok"}
    assert client.get("/api/v1/nope", headers=FETCH).status_code == 404
    assert client.get("/assets/missing.js").status_code == 404


def test_without_a_built_frontend_the_api_still_starts(tmp_path: Path) -> None:
    application = FastAPI()
    add_frontend(application, tmp_path / "missing")

    assert TestClient(application).get("/", headers=BROWSER).status_code == 404
