import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from urllib.parse import urlsplit

import feedparser
import httpx

from app.models import Language
from app.sources.base import (
    MIN_BODY_CHARS,
    Source,
    SourceItem,
    extract_text,
    is_recent,
)
from app.sources.http import Fetcher, RobotsDisallowed

log = logging.getLogger(__name__)


class FeedSource(Source):
    """An RSS feed, with the article text taken from the feed or from the article's page."""

    def __init__(
        self,
        key: str,
        url: str,
        *,
        path: str,
        text_in_feed: bool,
        language: Language = "en",
        official: bool = False,
        noise: re.Pattern[str] | None = None,
    ) -> None:
        self.key = key
        self.url = url
        self.path = path
        self.text_in_feed = text_in_feed
        self.language = language
        self.official = official
        self.noise = noise

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        feed = feedparser.parse(fetcher.get(self.url).content)
        now = datetime.now(UTC)
        for entry in feed.entries:
            link = entry.get("link", "")
            published = published_at(entry)
            if not urlsplit(link).path.startswith(self.path) or published is None:
                continue
            if not is_recent(published, now) or link in known:
                continue
            try:
                html = self._article_html(fetcher, entry)
            except (httpx.HTTPError, RobotsDisallowed) as error:
                log.warning("%s: skipped %s (%s)", self.key, link, error)
                continue
            body = extract_text(html, self.noise)
            if len(body) >= MIN_BODY_CHARS:
                yield SourceItem(url=link, title=entry.title, body=body, published_at=published)

    def _article_html(self, fetcher: Fetcher, entry: feedparser.FeedParserDict) -> str:
        if self.text_in_feed:
            content = entry.get("content")
            return content[0].value if content else ""
        return fetcher.get(entry.link).text


def published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*parsed[:6], tzinfo=UTC) if parsed else None
