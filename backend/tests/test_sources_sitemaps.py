import re
from datetime import UTC, datetime, timedelta

from app.sources.sitemaps import NewsSitemapSource
from tests.web import FakeWeb, article_html

SITEMAP = "https://club.example.com/en/sitemap/articles.xml"


def news_sitemap(entries: list[tuple[str, str, int]]) -> str:
    now = datetime.now(UTC)
    urls = "".join(
        f"<url><loc>{url}</loc><news:news><news:publication_date>"
        f"{(now - timedelta(hours=hours)).isoformat()}</news:publication_date>"
        f"<news:title>{title}</news:title></news:news></url>"
        for url, title, hours in entries
    )
    return (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'
        f"{urls}</urlset>"
    )


def test_sitemap_filters_sections_removes_noise_and_skips_known() -> None:
    base = "https://club.example.com/en"
    web = FakeWeb(
        {
            SITEMAP: news_sitemap(
                [
                    (f"{base}/football/first-team/news/1/win", "Football win", 3),
                    (f"{base}/handball/first-team/news/2/handball", "Handball", 3),
                    (f"{base}/basketball/first-team/news/3/known", "Known", 3),
                ]
            ),
            f"{base}/football/first-team/news/1/win": article_html(
                "Football win", extra=("- label.aria.whatsapp WhatsApp",)
            ),
        }
    )
    source = NewsSitemapSource(
        "club",
        SITEMAP,
        paths=("/en/football/first-team/", "/en/basketball/first-team/"),
        language="en",
        official=True,
        noise=re.compile(r"label\.aria"),
    )

    items = list(source.items(web.fetcher(), {f"{base}/basketball/first-team/news/3/known"}))

    assert [item.title for item in items] == ["Football win"]
    assert "label.aria" not in items[0].body
    assert f"{base}/basketball/first-team/news/3/known" not in web.urls()


def test_listing_adds_what_the_sitemap_misses_without_duplicates() -> None:
    sitemap = "https://acb.example.com/sitemaps/recent.xml"
    in_both = "https://acb.example.com/es/liga/noticias/cronica-1"
    only_listing = "https://acb.example.com/es/liga/noticias/cronica-2"
    listing_html = (
        '<a href="/es/liga/noticias/cronica-1">1</a><a href="/es/liga/noticias/cronica-2">2</a>'
    )
    published = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    web = FakeWeb(
        {
            sitemap: news_sitemap([(in_both, "Crónica 1", 5)]),
            in_both: article_html("Crónica 1"),
            "https://www.acb.example.com/es/liga/noticias": listing_html,
            only_listing: article_html("Crónica 2 (89-87)", date=published),
        }
    )
    source = NewsSitemapSource(
        "acb",
        sitemap,
        paths=("/es/liga/noticias/",),
        language="es",
        official=True,
        listing="https://www.acb.example.com/es/liga/noticias",
    )

    items = list(source.items(web.fetcher(), set()))

    assert [item.url for item in items] == [in_both, only_listing]
    assert items[1].title == "Crónica 2 (89-87)"
