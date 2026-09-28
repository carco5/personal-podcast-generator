import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, Episode, EpisodeArticle
from app.pipeline.common import EpisodeSkipped
from app.pipeline.selection import (
    Block,
    Picks,
    allocate,
    select_stories,
    sport_order,
    story_slots,
)
from tests.fakes import FakeLlm, make_article, make_listener, make_run

NOW = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)


def ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


def result(number: int, *teams: str) -> dict:
    return {"competition": "euroleague", "type": "result", "round": number, "teams": list(teams)}


def scenario(session: Session) -> None:
    make_article(
        session,
        "euroleague-api",
        "Barça beat Efes",
        ago(7),
        meta=result(1, "FC Barcelona", "Anadolu Efes"),
    )
    make_article(
        session,
        "euroleague-api",
        "Olympiacos beat Baskonia",
        ago(7),
        meta=result(1, "Olympiacos", "Baskonia"),
    )
    make_article(
        session,
        "euroleague-api",
        "Barça beat Dubai",
        ago(2),
        meta=result(2, "FC Barcelona", "Dubai"),
    )
    make_article(
        session,
        "euroleague-api",
        "Paris beat Partizan",
        ago(2),
        meta=result(2, "Paris", "Partizan"),
    )
    make_article(
        session,
        "euroleague-api",
        "Standings after Round 2",
        ago(1.5),
        body="1. FC Barcelona, 2 wins",
        meta={
            "competition": "euroleague",
            "type": "standings",
            "round": 2,
            "teams": ["FC Barcelona", "Dubai"],
        },
    )
    make_article(
        session,
        "euroleague-api",
        "Round 3 fixtures",
        ago(1),
        meta={
            "competition": "euroleague",
            "type": "fixtures",
            "round": 3,
            "games": [{"date": "2026-10-02", "home": "Besiktas", "away": "FC Barcelona"}],
        },
    )
    make_article(session, "eurohoops-euroleague", "Barça sign a guard", ago(1))
    make_article(session, "eurohoops-euroleague", "Real Madrid injury", ago(1))
    make_article(session, "eurohoops-euroleague", "Six days old", ago(6))
    make_article(
        session, "fcbarcelona", "Barça training report", ago(0.5), path="/en/basketball/first-team"
    )
    make_article(
        session, "fcbarcelona", "Barça lead LaLiga", ago(0.5), path="/en/football/first-team"
    )


def stories_by_block(session: Session, episode: Episode) -> dict[str, list[str]]:
    rows = session.scalars(
        select(EpisodeArticle).where(EpisodeArticle.episode_id == episode.id)
    ).all()
    titles = {row.source_id: session.get_one(Article, row.article_id).title for row in rows}
    return {
        block["key"]: [titles[sid] for story in block["stories"] for sid in story["source_ids"]]
        for block in episode.plan["blocks"]
    }


def test_story_slots_per_length() -> None:
    assert [story_slots(minutes) for minutes in (3, 5, 7)] == [4, 8, 12]


def test_allocation_covers_every_interest_then_follows_weight() -> None:
    def block(key: str, weight: str, available: int) -> Block:
        return Block(key, key, weight, stories=list(range(available)))

    blocks = [block("barca", "high", 10), block("euroleague", "medium", 10), block("nba", "low", 1)]
    allocate(blocks, 8)
    assert [b.wanted for b in blocks] == [4, 3, 1]

    small = [block("barca", "high", 1), block("nba", "low", 10)]
    allocate(small, 8)
    assert [b.wanted for b in small] == [1, 7]


def test_a_split_interest_shares_its_weight() -> None:
    def block(key: str, weight: str, available: int, interest: str = "") -> Block:
        return Block(key, key, weight, stories=list(range(available)), interest=interest)

    blocks = [
        block("barca-football", "high", 10, "barca"),
        block("barca-basketball", "high", 10, "barca"),
        block("euroleague", "medium", 10),
        block("acb", "medium", 10),
        block("nba", "low", 1),
    ]
    allocate(blocks, 8)

    assert [b.wanted for b in blocks] == [2, 1, 2, 2, 1]


def test_catch_up_assigns_each_story_to_one_block(session: Session) -> None:
    user, podcast, interests = make_listener(
        session, [("fc-barcelona", "high"), ("euroleague", "medium")]
    )
    scenario(session)
    run = make_run(session, user, podcast, interests, now=NOW)

    details = select_stories(run)

    blocks = stories_by_block(session, run.episode)
    assert list(blocks) == ["fc-barcelona-football", "fc-barcelona-basketball", "euroleague"]
    assert blocks["fc-barcelona-football"] == ["Barça lead LaLiga"]
    assert sorted(blocks["fc-barcelona-basketball"]) == [
        "Barça beat Dubai",
        "Barça sign a guard",
        "Barça training report",
    ]
    assert sorted(blocks["euroleague"]) == ["Paris beat Partizan", "Real Madrid injury"]
    football, basketball, euroleague = run.episode.plan["blocks"]
    assert (football["sport"], football["title"]) == ("football", "FC Barcelona · football")
    assert football["context_ids"] == []
    assert basketball["context_ids"] == euroleague["context_ids"]
    assert len(basketball["context_ids"]) == 2
    assert run.episode.plan["coverage"] == "catch-up: the listener's first episode"
    assert details["stories"] == 6
    assert "Pick up to 3 stories" in run.llm.prompts[0][1]
    assert "latest\n  result in each competition" in run.llm.instructions[0]


def test_club_results_are_guaranteed_by_code(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("fc-barcelona", "high")])
    scenario(session)
    make_article(
        session,
        "acb-calendar",
        "Barça beat Leyma",
        ago(1),
        meta={"competition": "liga-acb", "type": "result", "round": 1, "teams": ["Barça", "Leyma"]},
    )

    def news_only(prompt: str) -> Picks:
        guard = re.search(r"^\[(C\d+)\] \([^)]*\) Barça sign a guard", prompt, re.MULTILINE)
        story = {"source_ids": [guard.group(1)], "reason": "fake"}
        block = {"key": "fc-barcelona-basketball", "stories": [story]}
        return Picks.model_validate({"blocks": [block]})

    run = make_run(session, user, podcast, interests, llm=FakeLlm({Picks: news_only}), now=NOW)

    select_stories(run)

    blocks = {block["key"]: block for block in run.episode.plan["blocks"]}
    assert len(blocks["fc-barcelona-basketball"]["stories"]) == 1
    assert stories_by_block(session, run.episode)["fc-barcelona-basketball"] == [
        "Barça beat Leyma",
        "Barça beat Dubai",
        "Barça sign a guard",
    ]


def test_blocks_are_grouped_by_sport() -> None:
    blocks = [
        Block("barca-basketball", "", "high", "basketball"),
        Block("barca-football", "", "high", "football"),
        Block("f1", "", "high", None),
        Block("euroleague", "", "medium", "basketball"),
        Block("laliga", "", "low", "football"),
        Block("nba", "", "low", "basketball"),
    ]

    ordered = [block.key for block in sport_order(blocks)]

    assert ordered == ["barca-football", "laliga", "barca-basketball", "euroleague", "nba", "f1"]


def test_update_covers_only_what_is_new_and_untold(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("euroleague", "high")])
    told = make_article(session, "eurohoops-euroleague", "Told yesterday", ago(0.5))
    make_article(session, "eurohoops-euroleague", "Seen before the last episode", ago(2))
    make_article(session, "eurohoops-euroleague", "Brand new", ago(0.2))
    previous = Episode(
        user_id=user.id,
        trigger="scheduled",
        scheduled_for=ago(1),
        status="completed",
        audio_path="episodes/1.mp3",
        started_at=ago(1),
        finished_at=ago(1),
        plan={"selected_at": ago(1).isoformat()},
    )
    session.add(previous)
    session.flush()
    session.add(
        EpisodeArticle(
            episode_id=previous.id, article_id=told.id, source_id="S1", block="euroleague", rank=1
        )
    )
    session.flush()
    run = make_run(session, user, podcast, interests, now=NOW)

    select_stories(run)

    assert stories_by_block(session, run.episode) == {"euroleague": ["Brand new"]}
    assert run.episode.plan["coverage"] == "new since Wednesday 30 September 2026"


def test_nothing_new_skips_the_episode(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("nba", "high")])
    llm = FakeLlm()
    run = make_run(session, user, podcast, interests, llm=llm, now=NOW)

    with pytest.raises(EpisodeSkipped, match="No fresh news for your interests"):
        select_stories(run)
    assert llm.prompts == []


def test_invalid_picks_fall_back_to_recency(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("euroleague", "high")], length_minutes=3)
    make_article(session, "eurohoops-euroleague", "Newest", ago(0.1))
    make_article(session, "eurohoops-euroleague", "Older", ago(1))
    wrong = FakeLlm(
        {
            Picks: lambda prompt: Picks.model_validate(
                {
                    "blocks": [
                        {"key": "euroleague", "stories": [{"source_ids": ["C99"], "reason": "?"}]}
                    ]
                }
            )
        }
    )
    run = make_run(session, user, podcast, interests, llm=wrong, now=NOW)

    select_stories(run)

    assert stories_by_block(session, run.episode) == {"euroleague": ["Newest", "Older"]}
    assert run.episode.plan["blocks"][0]["stories"][0]["reason"] == "Chosen by recency"


def test_custom_topic_matches_headline_or_repeated_mentions(session: Session) -> None:
    user, podcast, interests = make_listener(session, [("Formula 1", "high", ["Formula 1", "F1"])])
    make_article(session, "cbs-nba", "F1 star visits the Lakers", ago(0.5))
    make_article(session, "cbs-nba", "Lakers notes", ago(0.5), body="F1 and more F1 talk.")
    make_article(session, "cbs-nba", "Celtics notes", ago(0.5), body="He likes Formula 1.")
    run = make_run(session, user, podcast, interests, now=NOW)

    select_stories(run)

    assert sorted(stories_by_block(session, run.episode)["Formula 1"]) == [
        "F1 star visits the Lakers",
        "Lakers notes",
    ]
