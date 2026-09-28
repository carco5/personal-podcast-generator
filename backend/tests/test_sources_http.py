import httpx
import pytest

from app.sources.http import USER_AGENT, Fetcher, RobotsDisallowed
from tests.web import FakeWeb

ESPN_ROBOTS = "User-agent: *\nDisallow: */boxscore?\n"
LALIGA_ROBOTS = "User-agent: *\nAllow: /en-GB/\nDisallow: /en-*/*\nDisallow: /es-*/*\n"


def test_wildcard_rules_are_honoured() -> None:
    web = FakeWeb({"https://www.espn.com/robots.txt": ESPN_ROBOTS})
    fetcher = web.fetcher()

    assert fetcher.allowed("https://www.espn.com/nba/story/_/id/1/x")
    assert not fetcher.allowed("https://www.espn.com/nba/boxscore?gameId=1")


def test_allow_wins_a_tie_with_disallow() -> None:
    web = FakeWeb({"https://www.laliga.com/robots.txt": LALIGA_ROBOTS})
    fetcher = web.fetcher()

    assert fetcher.allowed("https://www.laliga.com/en-GB/laliga-easports/standing")
    assert not fetcher.allowed("https://www.laliga.com/es-ES/noticias/")


def test_a_disallowed_url_is_never_requested() -> None:
    web = FakeWeb({"https://www.espn.com/robots.txt": ESPN_ROBOTS})

    with pytest.raises(RobotsDisallowed):
        web.fetcher().get("https://www.espn.com/nba/boxscore?gameId=1")
    assert web.urls() == ["https://www.espn.com/robots.txt"]


def test_missing_robots_allows_everything_and_is_read_once() -> None:
    web = FakeWeb({"https://example.com/a": "A", "https://example.com/b": "B"})
    fetcher = web.fetcher()

    fetcher.get("https://example.com/a")
    fetcher.get("https://example.com/b")

    assert web.urls().count("https://example.com/robots.txt") == 1


def test_requests_to_the_same_site_are_spaced() -> None:
    web = FakeWeb(
        {
            "https://a.example/1": "A1",
            "https://a.example/2": "A2",
            "https://b.example/1": "B1",
            "https://c.example/robots.txt": "User-agent: *\nCrawl-delay: 3\n",
            "https://c.example/1": "C1",
            "https://c.example/2": "C2",
        }
    )
    fetcher = Fetcher(httpx.MockTransport(web.handle), min_interval=1.0)
    waits: list[float] = []
    fetcher._clock = lambda: 100.0
    fetcher._sleep = waits.append

    for url in ["a.example/1", "b.example/1", "a.example/2", "c.example/1", "c.example/2"]:
        fetcher.get(f"https://{url}")

    assert waits == [1.0, 3.0]


def test_a_robots_server_error_blocks_the_site() -> None:
    web = FakeWeb({"https://example.com/robots.txt": httpx.Response(503)})

    with pytest.raises(httpx.HTTPStatusError):
        web.fetcher().get("https://example.com/a")
    assert "https://example.com/a" not in web.urls()


def test_requests_carry_the_user_agent_and_fail_on_errors() -> None:
    web = FakeWeb({"https://example.com/gone": httpx.Response(410)})

    with pytest.raises(httpx.HTTPStatusError):
        web.fetcher().get("https://example.com/gone")
    assert all(request.headers["User-Agent"] == USER_AGENT for request in web.requests)
