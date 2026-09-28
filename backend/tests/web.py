import json

import httpx

from app.sources.http import Fetcher

PARAGRAPH = (
    "The home side controlled the game after a strong second half, with the bench scoring "
    "freely and the defence holding firm in the final minutes."
)


def article_html(title: str, extra: tuple[str, ...] = (), date: str | None = None) -> str:
    paragraphs = "".join(f"<p>Part {number}. {PARAGRAPH}</p>" for number in range(1, 5))
    lines = "".join(f"<p>{line}</p>" for line in extra)
    json_ld = f'<script>{{"datePublished":"{date}"}}</script>' if date else ""
    return (
        f"<html><head><title>{title}</title>{json_ld}</head><body><nav>Home News</nav>"
        f"<article><h1>{title}</h1>{lines}{paragraphs}</article><footer>Cookies</footer>"
        "</body></html>"
    )


class FakeWeb:
    def __init__(self, routes: dict[str, object]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(str(request.url.copy_with(query=None)))
        if route is None:
            return httpx.Response(404)
        if isinstance(route, httpx.Response):
            return route
        if isinstance(route, str):
            return httpx.Response(200, text=route)
        return httpx.Response(200, text=json.dumps(route))

    def fetcher(self) -> Fetcher:
        return Fetcher(httpx.MockTransport(self.handle))

    def urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]
