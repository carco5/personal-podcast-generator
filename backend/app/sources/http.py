import time
from urllib.parse import urlsplit

import httpx
from protego import Protego

USER_AGENT = "PersonalPodcastBot/0.1 (+https://github.com/carco5/personal-podcast-generator)"
TIMEOUT_SECONDS = 20
POLITE_SECONDS = 1.0


class RobotsDisallowed(Exception):
    """The site's robots.txt does not allow this URL for our user agent."""


class Fetcher:
    """GETs URLs like a responsible crawler: honest User-Agent, robots.txt and a timeout."""

    def __init__(
        self, transport: httpx.BaseTransport | None = None, *, min_interval: float | None = None
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            transport=transport,
        )
        self._robots: dict[str, Protego | None] = {}
        default = POLITE_SECONDS if transport is None else 0.0
        self._min_interval = default if min_interval is None else min_interval
        self._last: dict[str, float] = {}
        self._clock = time.monotonic
        self._sleep = time.sleep

    def close(self) -> None:
        self._client.close()

    def get(
        self,
        url: str,
        params: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if not self.allowed(url):
            raise RobotsDisallowed(url)
        self._wait_turn(url)
        response = self._client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response

    def _wait_turn(self, url: str) -> None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        rules = self._robots.get(origin)
        asked = (rules.crawl_delay(USER_AGENT) if rules else None) or 0.0
        delay = max(self._min_interval, asked)
        if origin in self._last:
            remaining = delay - (self._clock() - self._last[origin])
            if remaining > 0:
                self._sleep(remaining)
        self._last[origin] = self._clock()

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._read_robots(origin)
        rules = self._robots[origin]
        return rules is None or rules.can_fetch(url, USER_AGENT)

    def _read_robots(self, origin: str) -> Protego | None:
        response = self._client.get(f"{origin}/robots.txt")
        if response.status_code == 200:
            return Protego.parse(response.text)
        if 400 <= response.status_code < 500:
            return None
        response.raise_for_status()
        raise httpx.HTTPError(f"Unexpected robots.txt status {response.status_code}")
