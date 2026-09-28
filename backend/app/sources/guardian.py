from collections.abc import Iterator
from datetime import UTC, datetime

from pydantic import SecretStr

from app.sources.base import (
    MAX_AGE,
    MAX_BODY_CHARS,
    MIN_BODY_CHARS,
    Source,
    SourceItem,
    parse_datetime,
)
from app.sources.http import Fetcher

SEARCH = "https://content.guardianapis.com/search"
PAGE_SIZE = 50


class GuardianSource(Source):
    """A Guardian section, by tag, as a catalogue source. It needs a (free) API key."""

    def __init__(self, key: str, tag: str, api_key: SecretStr) -> None:
        self.key = key
        self.tag = tag
        self.api_key = api_key
        self.language = "en"
        self.official = False

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        yield from search(fetcher, self.api_key, known, tag=self.tag)


def search(
    fetcher: Fetcher,
    api_key: SecretStr,
    known: set[str],
    *,
    tag: str | None = None,
    query: str | None = None,
) -> Iterator[SourceItem]:
    since = datetime.now(UTC) - MAX_AGE
    params: dict[str, str | int] = {
        "from-date": since.date().isoformat(),
        "show-fields": "bodyText",
        "page-size": PAGE_SIZE,
        "order-by": "newest",
    }
    if tag is not None:
        params["tag"] = tag
    if query is not None:
        params["q"] = query
    response = fetcher.get(SEARCH, params=params, headers={"api-key": api_key.get_secret_value()})
    for result in response.json()["response"]["results"]:
        body = result.get("fields", {}).get("bodyText", "")[:MAX_BODY_CHARS]
        url = result["webUrl"]
        if result["type"] != "article" or url in known or len(body) < MIN_BODY_CHARS:
            continue
        yield SourceItem(
            url=url,
            title=result["webTitle"],
            body=body,
            published_at=parse_datetime(result["webPublicationDate"]),
        )


class GuardianSearchSource(Source):
    """A Guardian search for a listener's own keywords."""

    key = "guardian-search"
    language = "en"
    official = False

    def __init__(self, query: str, api_key: SecretStr) -> None:
        self.query = query
        self.api_key = api_key

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        yield from search(fetcher, self.api_key, known, query=self.query)
