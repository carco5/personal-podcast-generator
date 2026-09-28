from urllib.parse import urlsplit

import httpx
from protego import Protego

USER_AGENT = "PersonalPodcastBot/0.1 (+https://github.com/carco5/personal-podcast-generator)"
TIMEOUT_SECONDS = 20


class RobotsDisallowed(Exception):
    """The site's robots.txt does not allow this URL for our user agent."""


class Fetcher:
    """GETs URLs like a responsible crawler: honest User-Agent, robots.txt and a timeout."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            transport=transport,
        )
        self._robots: dict[str, Protego | None] = {}

    def get(
        self,
        url: str,
        params: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if not self.allowed(url):
            raise RobotsDisallowed(url)
        response = self._client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response

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
