import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.pipeline.common import StageFailed
from app.pipeline.fetch import episode_sources, fetch
from app.sources.http import Fetcher
from tests.fakes import make_listener, make_run


def test_a_team_brings_the_sources_of_its_competitions(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("fc-barcelona-basketball", "high")])
    run = make_run(session, user, podcast, interests)

    sources = set(episode_sources(run))

    assert {"fcbarcelona", "euroleague-api", "acb-calendar", "acb-news"} <= sources
    assert not {"laliga-data", "uefa-news", "espn-nba"} & sources
    assert not any(key.startswith("guardian") for key in sources)


def test_custom_topics_search_everything_and_the_guardian(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("Formula 1", "low", ["Formula 1", "F1"])])
    run = make_run(session, user, podcast, interests)
    run.config.guardian_api_key = SecretStr("key")

    sources = episode_sources(run)

    assert {"espn-nba", "laliga-data", "guardian-laliga", "guardian-search"} <= set(sources)
    assert sources["guardian-search"].query == '"Formula 1" OR "F1"'


def test_fetch_fails_when_every_source_fails(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("nba", "high")])
    run = make_run(session, user, podcast, interests)
    run.fetcher = Fetcher(httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(StageFailed, match="every source failed"):
        fetch(run)
