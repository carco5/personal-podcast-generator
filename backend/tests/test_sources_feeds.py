from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx

from app.sources.feeds import FeedSource
from tests.web import PARAGRAPH, FakeWeb, article_html

FEED = "https://news.example.com/nba/feed"


def rss(entries: list[tuple[str, str, int, str | None]]) -> str:
    now = datetime.now(UTC)
    items = "".join(
        f"<item><title>{title}</title><link>https://news.example.com{path}</link>"
        f"<pubDate>{format_datetime(now - timedelta(hours=hours))}</pubDate>"
        + (f"<content:encoded><![CDATA[{html}]]></content:encoded>" if html else "")
        + "</item>"
        for path, title, hours, html in entries
    )
    return (
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">'
        f"<channel><title>News</title>{items}</channel></rss>"
    )


def test_feed_keeps_only_recent_full_articles_from_its_section() -> None:
    web = FakeWeb(
        {
            FEED: rss(
                [
                    ("/nba/news/good", "Good", 2, article_html("Good")),
                    ("/nfl/news/other-sport", "NFL", 2, article_html("NFL")),
                    ("/nba/news/old", "Old", 5 * 24, article_html("Old")),
                    ("/nba/news/short", "Short", 2, f"<p>{PARAGRAPH}</p>"),
                    ("/nba/news/known", "Known", 2, article_html("Known")),
                ]
            )
        }
    )
    source = FeedSource("test-feed", FEED, path="/nba/news/", text_in_feed=True)

    items = list(source.items(web.fetcher(), {"https://news.example.com/nba/news/known"}))

    assert [item.title for item in items] == ["Good"]
    assert items[0].kind == "article" and len(items[0].body) >= 500


def test_feed_without_text_reads_each_page_and_skips_broken_ones() -> None:
    web = FakeWeb(
        {
            FEED: rss([("/nba/story/a", "A", 1, None), ("/nba/story/b", "B", 1, None)]),
            "https://news.example.com/nba/story/a": article_html("A"),
            "https://news.example.com/nba/story/b": httpx.Response(404),
        }
    )
    source = FeedSource("test-feed", FEED, path="/nba/story/", text_in_feed=False)

    items = list(source.items(web.fetcher(), set()))

    assert [item.url for item in items] == ["https://news.example.com/nba/story/a"]
