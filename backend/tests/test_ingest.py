from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import CATALOG
from app.config import Settings
from app.models import Article, Episode, EpisodeArticle, User
from app.sources.base import Source, SourceItem
from app.sources.http import Fetcher
from app.sources.ingest import ingest
from app.sources.registry import (
    BARCA_HEADLINE,
    SOURCE_NAMES,
    TOPIC_FEEDS,
    catalogue_sources,
    source_sport,
)


class FakeSource(Source):
    def __init__(self, key: str, items: list[SourceItem]) -> None:
        self.key = key
        self.language = "en"
        self.official = False
        self._items = items
        self.known: set[str] = set()

    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        self.known = known
        yield from self._items


class BrokenSource(FakeSource):
    def items(self, fetcher: Fetcher, known: set[str]) -> Iterator[SourceItem]:
        raise KeyError("data")


def item(url: str, body: str = "Body", kind: str = "article") -> SourceItem:
    return SourceItem(url=url, title="Title", body=body, published_at=datetime.now(UTC), kind=kind)


def test_a_failing_source_does_not_stop_the_others(session: Session) -> None:
    good = FakeSource("good", [item("https://a.example/1"), item("https://a.example/2")])

    report = ingest(session, [BrokenSource("broken", []), good], Fetcher())

    assert report["broken"] == {"error": "KeyError: 'data'"}
    assert report["good"] == {"items": 2, "saved": 2}
    saved = session.scalars(select(Article)).all()
    assert {(a.source, a.language, a.official) for a in saved} == {("good", "en", False)}


def test_a_source_that_fails_to_save_does_not_stop_the_others(session: Session) -> None:
    broken = FakeSource("broken", [item("https://a.example/bad")])
    broken.language = "fr"
    good = FakeSource("good", [item("https://a.example/ok")])

    report = ingest(session, [broken, good], Fetcher())

    assert report["broken"]["error"].startswith("IntegrityError:")
    assert "ck_articles_language" in report["broken"]["error"]
    assert "INSERT" not in report["broken"]["error"]
    assert report["good"] == {"items": 1, "saved": 1}


def test_a_repeated_url_in_one_batch_is_saved_once(session: Session) -> None:
    source = FakeSource("s", [item("https://a.example/same"), item("https://a.example/same")])

    report = ingest(session, [source], Fetcher())

    assert report["s"] == {"items": 2, "saved": 1}


def test_known_urls_articles_are_kept_and_data_is_updated(session: Session) -> None:
    ingest(
        session,
        [
            FakeSource(
                "s", [item("https://a.example/n", "v1"), item("https://a.example/d", "v1", "data")]
            )
        ],
        Fetcher(),
    )
    second = FakeSource(
        "s", [item("https://a.example/n", "v2"), item("https://a.example/d", "v2", "data")]
    )

    report = ingest(session, [second], Fetcher())

    assert second.known == {"https://a.example/n", "https://a.example/d"}
    assert report["s"] == {"items": 2, "saved": 1}
    bodies = dict(session.execute(select(Article.url, Article.body)).all())
    assert bodies == {"https://a.example/n": "v1", "https://a.example/d": "v2"}


def test_refresh_rereads_stored_items(session: Session) -> None:
    ingest(session, [FakeSource("s", [item("https://a.example/d", "v1", "data")])], Fetcher())
    again = FakeSource("s", [item("https://a.example/d", "v1 with scorers", "data")])

    report = ingest(session, [again], Fetcher(), refresh=True)

    assert again.known == set()
    assert report["s"] == {"items": 1, "saved": 1}
    assert session.scalars(select(Article.body)).one() == "v1 with scorers"


def test_data_is_updated_when_only_its_meta_changes(session: Session) -> None:
    first = item("https://a.example/table", "Table", "data")
    ingest(session, [FakeSource("s", [first])], Fetcher())
    with_teams = first.model_copy(update={"meta": {"teams": ["FC Barcelona"]}})

    changed = ingest(session, [FakeSource("s", [with_teams])], Fetcher())
    same = ingest(session, [FakeSource("s", [with_teams])], Fetcher())

    assert changed["s"]["saved"] == 1 and same["s"]["saved"] == 0
    assert session.scalars(select(Article.meta)).one() == {"teams": ["FC Barcelona"]}


def test_purge_keeps_recent_and_used_sources(session: Session) -> None:
    ingest(
        session,
        [FakeSource("s", [item(f"https://a.example/{name}") for name in ("old", "used", "new")])],
        Fetcher(),
    )
    articles = {a.url.rsplit("/", 1)[1]: a for a in session.scalars(select(Article))}
    for name in ("old", "used"):
        articles[name].fetched_at = datetime.now(UTC) - timedelta(days=40)
    user = User(email="listener@example.com", name="Listener")
    session.add(user)
    session.flush()
    episode = Episode(user_id=user.id, trigger="manual", scheduled_for=func.now())
    session.add(episode)
    session.flush()
    session.add(
        EpisodeArticle(
            episode_id=episode.id, article_id=articles["used"].id, source_id="S1", block="x", rank=1
        )
    )
    session.flush()

    report = ingest(session, [], Fetcher())

    assert report["purged"] == {"articles": 1}
    assert {a.url.rsplit("/", 1)[1] for a in session.scalars(select(Article))} == {"used", "new"}


def test_every_catalogue_topic_is_wired_to_existing_sources() -> None:
    with_key = catalogue_sources(Settings(_env_file=None, guardian_api_key=SecretStr("k")))
    without_key = catalogue_sources(Settings(_env_file=None, guardian_api_key=None))

    assert set(TOPIC_FEEDS) == set(CATALOG)
    assert {key for feed in TOPIC_FEEDS.values() for key in feed.sources} <= set(with_key)
    assert not any(key.startswith("guardian") for key in without_key)
    assert set(with_key) | {"guardian-search"} == set(SOURCE_NAMES)


def test_team_sections_follow_the_competitions_of_their_sport() -> None:
    for key, feed in TOPIC_FEEDS.items():
        topic = CATALOG[key]
        assert (topic.kind == "team") == bool(feed.competitions), key
        assert all(CATALOG[c].sport == topic.sport for c in feed.competitions), key
        if feed.headline is None:
            assert all(source_sport(source, "") == topic.sport for source in feed.sources), key
    assert TOPIC_FEEDS["fc-barcelona-basketball"].competitions == ("euroleague", "liga-acb")


def test_team_headline_pattern() -> None:
    for headline in ("Barça sign a guard", "FC Barcelona win", "Barcelona beat Efes", "Barca 3-1"):
        assert BARCA_HEADLINE.search(headline), headline
    assert not BARCA_HEADLINE.search("Elche beat RCD Espanyol de Barcelona 3–1")
