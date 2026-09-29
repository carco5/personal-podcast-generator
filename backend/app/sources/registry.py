import re

from pydantic import BaseModel, ConfigDict

from app.catalog import CATALOG, SPORTS, Sport
from app.config import Settings
from app.sources.acb import AcbCalendarSource
from app.sources.base import Source
from app.sources.euroleague import EuroleagueSource
from app.sources.feeds import FeedSource
from app.sources.guardian import GuardianSource
from app.sources.laliga import LaLigaSource
from app.sources.sitemaps import NewsSitemapSource
from app.sources.uefa import UefaChampionsSource

FCB_NOISE = re.compile(r"label\.aria")
UEFA_NOISE = re.compile(r"^Article (summary|top media content|body)$")


def catalogue_sources(settings: Settings) -> dict[str, Source]:
    sources: list[Source] = [
        EuroleagueSource(),
        FeedSource(
            "eurohoops-euroleague",
            "https://www.eurohoops.net/en/category/euroleague/feed/",
            path="/en/",
            text_in_feed=True,
        ),
        FeedSource(
            "sportando-euroleague",
            "https://sportando.basketball/en/category/euroleague/feed/",
            path="/en/",
            text_in_feed=True,
        ),
        AcbCalendarSource(),
        NewsSitemapSource(
            "acb-news",
            "https://acb.com/sitemaps/noticias-recientes/sitemap.xml",
            paths=("/es/liga/noticias/",),
            language="es",
            official=True,
            listing="https://www.acb.com/es/liga/noticias",
        ),
        NewsSitemapSource(
            "fcbarcelona",
            "https://www.fcbarcelona.com/en/sitemap/articles/detailed.xml",
            paths=("/en/football/first-team/", "/en/basketball/first-team/"),
            language="en",
            official=True,
            noise=FCB_NOISE,
        ),
        FeedSource(
            "espn-nba",
            "https://www.espn.com/espn/rss/nba/news",
            path="/nba/story/",
            text_in_feed=False,
        ),
        FeedSource(
            "cbs-nba",
            "https://www.cbssports.com/rss/headlines/nba/",
            path="/nba/news/",
            text_in_feed=False,
        ),
        LaLigaSource(),
        UefaChampionsSource(),
        NewsSitemapSource(
            "uefa-news",
            "https://www.uefa.com/sitemap/news/latest.xml",
            paths=("/uefachampionsleague/",),
            language="en",
            official=True,
            noise=UEFA_NOISE,
        ),
    ]
    if settings.guardian_api_key is not None:
        key = settings.guardian_api_key
        sources += [
            GuardianSource("guardian-laliga", "football/laligafootball", key),
            GuardianSource("guardian-champions-league", "football/championsleague", key),
        ]
    return {source.key: source for source in sources}


SOURCE_NAMES = {
    "euroleague-api": "EuroLeague",
    "eurohoops-euroleague": "Eurohoops",
    "sportando-euroleague": "Sportando",
    "acb-calendar": "Liga ACB",
    "acb-news": "Liga ACB",
    "fcbarcelona": "FC Barcelona",
    "espn-nba": "ESPN",
    "cbs-nba": "CBS Sports",
    "laliga-data": "LaLiga",
    "uefa-news": "UEFA",
    "uefa-data": "UEFA",
    "guardian-laliga": "The Guardian",
    "guardian-champions-league": "The Guardian",
    "guardian-search": "The Guardian",
}


class TopicFeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    sources: tuple[str, ...]
    headline: re.Pattern[str] | None = None
    data_names: frozenset[str] = frozenset()
    competitions: tuple[str, ...] = ()


BARCA_HEADLINE = re.compile(r"\bBar[cç]a\b|\bFC Barcelona\b|(?<!Espanyol de )\bBarcelona\b")
BARCA_NAMES = frozenset({"FC Barcelona", "Barça", "Barcelona"})

TOPIC_FEEDS: dict[str, TopicFeed] = {
    "fc-barcelona-football": TopicFeed(
        sources=("fcbarcelona",),
        headline=BARCA_HEADLINE,
        data_names=BARCA_NAMES,
        competitions=("laliga", "champions-league"),
    ),
    "fc-barcelona-basketball": TopicFeed(
        sources=("fcbarcelona",),
        headline=BARCA_HEADLINE,
        data_names=BARCA_NAMES,
        competitions=("euroleague", "liga-acb"),
    ),
    "laliga": TopicFeed(sources=("laliga-data", "guardian-laliga")),
    "champions-league": TopicFeed(sources=("uefa-data", "uefa-news", "guardian-champions-league")),
    "euroleague": TopicFeed(
        sources=("euroleague-api", "eurohoops-euroleague", "sportando-euroleague")
    ),
    "liga-acb": TopicFeed(sources=("acb-calendar", "acb-news")),
    "nba": TopicFeed(sources=("espn-nba", "cbs-nba")),
}


def source_sport(source: str, url: str) -> Sport | None:
    if source == "fcbarcelona":
        return next((sport for sport in SPORTS if f"/{sport}/" in url), None)
    for key, feed in TOPIC_FEEDS.items():
        if feed.headline is None and source in feed.sources:
            return CATALOG[key].sport
    return None
