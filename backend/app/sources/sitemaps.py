import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import httpx
import trafilatura

from app.models import Language
from app.sources.base import (
    MIN_BODY_CHARS,
    Source,
    SourceItem,
    extract_text,
    is_recent,
    parse_datetime,
)
from app.sources.http import Fetcher, RobotsDisallowed

log = logging.getLogger(__name__)

NAMESPACES = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}
DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')


class NewsSitemapSource(Source):
    """A Google News sitemap, and optionally a news listing page, of an official website."""

    def __init__(
        self,
        key: str,
        url: str,
        *,
        paths: tuple[str, ...],
        language: Language,
        official: bool,
        noise: re.Pattern[str] | None = None,
        listing: str | None = None,
    ) -> None:
        self.key = key
        self.url = url
        self.paths = paths
        self.language = language
        self.official = official
        self.noise = noise
        self.listing = listing

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        now = datetime.now(UTC)
        seen: set[str] = set()
        for url, title, published in self._sitemap_entries(fetcher):
            seen.add(url)
            if self._wanted(url) and is_recent(published, now) and url not in known:
                item = self._item(fetcher, url, title, published)
                if item is not None:
                    yield item
        if self.listing is not None:
            yield from self._listing_items(fetcher, known | seen, now)

    def _sitemap_entries(self, fetcher: Fetcher) -> Iterator[tuple[str, str, datetime]]:
        root = ElementTree.fromstring(fetcher.get(self.url).content)
        for node in root.iterfind("sm:url", NAMESPACES):
            url = node.findtext("sm:loc", namespaces=NAMESPACES)
            title = node.findtext("news:news/news:title", namespaces=NAMESPACES)
            date = node.findtext("news:news/news:publication_date", namespaces=NAMESPACES)
            if url and title and date:
                yield url.strip(), title.strip(), parse_datetime(date.strip())

    def _wanted(self, url: str) -> bool:
        return any(urlsplit(url).path.startswith(path) for path in self.paths)

    def _item(
        self, fetcher: Fetcher, url: str, title: str, published: datetime
    ) -> SourceItem | None:
        try:
            html = fetcher.get(url).text
        except (httpx.HTTPError, RobotsDisallowed) as error:
            log.warning("%s: skipped %s (%s)", self.key, url, error)
            return None
        body = extract_text(html, self.noise)
        if len(body) < MIN_BODY_CHARS:
            return None
        return SourceItem(url=url, title=title, body=body, published_at=published)

    def _listing_items(
        self, fetcher: Fetcher, skip: set[str], now: datetime
    ) -> Iterator[SourceItem]:
        html = fetcher.get(self.listing).text
        paths = sorted(set(re.findall(r'href="(/[^"#?]+)"', html)))
        for path in paths:
            url = urljoin(self.url, path)
            if not self._wanted(url) or url in skip:
                continue
            try:
                page = fetcher.get(url).text
            except (httpx.HTTPError, RobotsDisallowed) as error:
                log.warning("%s: skipped %s (%s)", self.key, url, error)
                continue
            metadata = trafilatura.extract_metadata(page)
            date = DATE_PUBLISHED.search(page)
            if metadata is None or not metadata.title or date is None:
                continue
            published = parse_datetime(date.group(1))
            body = extract_text(page, self.noise)
            if is_recent(published, now) and len(body) >= MIN_BODY_CHARS:
                yield SourceItem(url=url, title=metadata.title, body=body, published_at=published)
