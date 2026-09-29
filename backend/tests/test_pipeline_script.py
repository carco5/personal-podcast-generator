from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.models import EpisodeArticle
from app.pipeline.checks import Judgement, check_script
from app.pipeline.common import Run, StageFailed
from app.pipeline.repair import Repairs
from app.pipeline.script import Script, write_script
from tests.fakes import FakeLlm, approve_all, make_article, make_listener, make_run
from tests.test_pipeline_checks import GOOD, PLAN, SOURCES

NOW = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)


def planned_run(session: Session, llm: FakeLlm) -> Run:
    user, podcast, interests = make_listener(session, [("euroleague", "high")])
    run = make_run(session, user, podcast, interests, llm=llm, now=NOW)
    for source_id, source, kind in (
        ("S1", "euroleague-api", {"competition": "euroleague", "type": "result", "round": 2}),
        ("S2", "acb-news", None),
        ("S3", "euroleague-api", {"competition": "euroleague", "type": "fixtures", "round": 3}),
    ):
        title, _, body = SOURCES[source_id].text.partition("\n")
        article = make_article(session, source, title, NOW, body=body or title, meta=kind)
        article.language = SOURCES[source_id].language
        article.official = True
        session.add(
            EpisodeArticle(
                episode_id=run.episode.id,
                article_id=article.id,
                source_id=source_id,
                block="euroleague",
                rank=1,
            )
        )
    run.episode.plan = PLAN
    session.flush()
    return run


def judge(flags: dict[str, str] | None = None) -> Callable[[str], Judgement]:
    return lambda prompt: approve_all(prompt, flags)


def test_write_sends_plan_sources_and_settings(session: Session) -> None:
    llm = FakeLlm({Script: lambda prompt: Script.model_validate(GOOD)})
    run = planned_run(session, llm)

    details = write_script(run)

    _, prompt = llm.prompts[0]
    instructions = llm.instructions[0]
    assert "[CTX] Today is Thursday 1 October 2026 [say: today]." in prompt
    assert "Hook: Barça won in Dubai. (sources S1)" in prompt
    assert 'Segment "euroleague" (EuroLeague): about 230 characters, about 2 turns.' in prompt
    assert "    - Punter scored 19 points. (sources S1)" in prompt
    assert "  Roundup: S2" in prompt
    assert "Friday 2 October 2026 [say: tomorrow]: Besiktas host FC Barcelona" in prompt
    assert "Besiktas host FC Barcelona.\nEuroLeague Round 3 fixtures." in prompt
    assert "Published: Thursday 1 October 2026 [say: today]" in prompt
    assert "[S2] Official · Liga ACB" in prompt
    assert '"Test Show"' in instructions
    assert "introduces George and Sarah by name" in instructions
    assert "never list every section" in instructions
    assert "Days: never say a full date" in instructions
    assert "At most two stock openers" in instructions
    assert "about one audio tag every four or five turns" in instructions
    assert 'say "a performance rating of 30"' in instructions
    assert "Now, basketball" not in instructions
    assert run.episode.title == "Barça win in Dubai"
    assert details["segments"] == 3 and not details["rewrite"]


def test_a_supported_script_passes(session: Session) -> None:
    llm = FakeLlm({Judgement: judge()})
    run = planned_run(session, llm)
    run.episode.script = GOOD

    details = check_script(run)

    assert details == {"rounds": [{"problems": [], "judged": True, "style": []}], "warnings": []}
    assert "compare the meaning across languages" in llm.instructions[0]
    assert '"triple" is a three-pointer' in llm.instructions[0]


def test_flagged_turns_are_repaired_not_the_whole_script(session: Session) -> None:
    verdicts = iter([judge({"euroleague.3": "unsupported"}), judge()])
    llm = FakeLlm({Judgement: lambda prompt: next(verdicts)(prompt)})
    run = planned_run(session, llm)
    bad = Script.model_validate(GOOD).model_dump()
    bad["segments"][1]["turns"][1]["text"] = "Kevin Punter scored 21 points."
    run.episode.script = bad

    details = check_script(run)

    assert [schema for schema, _ in llm.prompts] == [Judgement, Repairs, Judgement]
    repair_prompt = llm.prompts[1][1]
    assert "the numbers ['21']" in repair_prompt
    assert "unsupported: fake" in repair_prompt
    rejudged = llm.prompts[2][1].split("TURNS")[1]
    assert "[euroleague.2]" in rejudged and "[euroleague.3]" in rejudged
    assert "[euroleague.1]" not in rejudged
    assert details["repaired"] == ["euroleague.2", "euroleague.3"] and details["removed"] == []
    fixed = Script.model_validate(run.episode.script)
    assert fixed.segments[1].turns[1].text == "That's the one to watch."


@pytest.mark.parametrize(
    "verdict", ["unsupported", "contradicted", "overstated", "misattributed", "wrong_time"]
)
def test_a_turn_that_stays_wrong_is_removed(session: Session, verdict: str) -> None:
    llm = FakeLlm({Judgement: judge({"euroleague.3": verdict})})
    run = planned_run(session, llm)
    run.episode.script = GOOD

    details = check_script(run)

    assert [removed["turn"] for removed in details["removed"]] == ["euroleague.3"]
    assert verdict in details["removed"][0]["problems"][0]
    turns = Script.model_validate(run.episode.script).segments[1].turns
    assert len(turns) == len(GOOD["segments"][1]["turns"]) - 1


def test_losing_a_lead_story_fails_the_episode(session: Session) -> None:
    flags = {"euroleague.1": "unsupported", "euroleague.2": "unsupported"}
    llm = FakeLlm({Judgement: judge(flags)})
    run = planned_run(session, llm)
    run.episode.script = GOOD

    with pytest.raises(StageFailed, match="the lead story was lost") as failure:
        check_script(run)

    removed = [item["turn"] for item in failure.value.details["removed"]]
    assert removed == ["euroleague.1", "euroleague.2"]


def test_a_script_problem_is_rewritten_and_fails_if_it_stays(session: Session) -> None:
    bad = Script.model_validate(GOOD).model_dump()
    bad["segments"].reverse()
    llm = FakeLlm({Judgement: judge(), Script: lambda prompt: Script.model_validate(bad)})
    run = planned_run(session, llm)
    run.episode.script = bad

    with pytest.raises(StageFailed, match="failed twice") as failure:
        check_script(run)

    assert failure.value.details["rounds"][1]["judged"] is False
    assert [schema for schema, _ in llm.prompts] == [Judgement, Script]
    assert "segments must be exactly" in llm.prompts[1][1]


def test_a_turn_the_judge_skips_is_a_problem(session: Session) -> None:
    def lazy_judge(prompt: str) -> Judgement:
        return Judgement.model_validate({"verdicts": []})

    llm = FakeLlm({Judgement: lazy_judge})
    run = planned_run(session, llm)
    run.episode.script = GOOD

    with pytest.raises(StageFailed) as failure:
        check_script(run)

    assert "did not review this turn" in failure.value.details["rounds"][0]["problems"][0]
