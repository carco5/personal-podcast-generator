from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.models import EpisodeArticle
from app.pipeline.checks import Judgement, check_script
from app.pipeline.common import Run, StageFailed
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
    assert "[CTX] Today is Thursday 1 October 2026 [say: today]." in prompt
    assert "Friday 2 October 2026 [say: tomorrow]: Besiktas host FC Barcelona" in prompt
    assert 'Segment "euroleague" (EuroLeague; sport: basketball): about 760 characters.' in prompt
    assert "Say clearly when the episode moves to" in llm.instructions[0]
    assert "[S2] Official · Liga ACB" in prompt
    assert "George" in llm.instructions[0] and "Sarah" in llm.instructions[0]
    assert '"Test Show"' in llm.instructions[0]
    assert 'say "a performance rating of 30"' in llm.instructions[0]
    assert "mention each fixture only once" in llm.instructions[0]
    assert "Leave its details to its segment" in llm.instructions[0]
    assert "Say team names in full" in llm.instructions[0]
    assert 'never "that day" twice' in llm.instructions[0]
    assert "use 2 to 4 audio tags" in llm.instructions[0]
    assert run.episode.title == "Barça win in Dubai"
    assert details["segments"] == 3 and not details["rewrite"]


def test_a_supported_script_passes(session: Session) -> None:
    llm = FakeLlm({Judgement: judge()})
    run = planned_run(session, llm)
    run.episode.script = GOOD

    details = check_script(run)

    assert details == {"rounds": [{"problems": [], "judged": True}]}
    assert "compare the meaning across languages" in llm.instructions[0]
    assert '"triple" is a three-pointer' in llm.instructions[0]


def test_a_flagged_turn_is_rewritten_once(session: Session) -> None:
    verdicts = iter([judge({"euroleague.2": "unsupported"}), judge()])
    llm = FakeLlm(
        {
            Judgement: lambda prompt: next(verdicts)(prompt),
            Script: lambda prompt: Script.model_validate(GOOD),
        }
    )
    run = planned_run(session, llm)
    run.episode.script = GOOD

    details = check_script(run)

    assert [schema for schema, _ in llm.prompts] == [Judgement, Script, Judgement]
    rewrite_prompt = llm.prompts[1][1]
    assert "YOUR PREVIOUS SCRIPT" in rewrite_prompt
    assert "euroleague.2: unsupported: fake" in rewrite_prompt
    assert len(details["rounds"]) == 2 and details["rounds"][1]["problems"] == []


@pytest.mark.parametrize(
    "verdict", ["unsupported", "contradicted", "overstated", "misattributed", "wrong_time"]
)
def test_a_second_judge_failure_fails_the_episode(session: Session, verdict: str) -> None:
    llm = FakeLlm(
        {
            Judgement: judge({"euroleague.3": verdict}),
            Script: lambda prompt: Script.model_validate(GOOD),
        }
    )
    run = planned_run(session, llm)
    run.episode.script = GOOD

    with pytest.raises(StageFailed, match="failed twice") as failure:
        check_script(run)

    assert len(failure.value.details["rounds"]) == 2
    assert f"euroleague.3: {verdict}" in failure.value.details["rounds"][1]["problems"][0]


def test_the_first_round_judges_even_with_code_problems(session: Session) -> None:
    verdicts = iter([judge({"euroleague.3": "unsupported"}), judge()])
    llm = FakeLlm(
        {
            Judgement: lambda prompt: next(verdicts)(prompt),
            Script: lambda prompt: Script.model_validate(GOOD),
        }
    )
    run = planned_run(session, llm)
    bad = Script.model_validate(GOOD).model_dump()
    bad["segments"][1]["turns"][1]["text"] = "Kevin Punter scored 21 points."
    run.episode.script = bad

    details = check_script(run)

    assert details["rounds"][0]["judged"] is True
    assert [schema for schema, _ in llm.prompts] == [Judgement, Script, Judgement]
    rewrite_prompt = llm.prompts[1][1]
    assert "the numbers ['21']" in rewrite_prompt
    assert "euroleague.3: unsupported: fake" in rewrite_prompt
    assert details["rounds"][1]["problems"] == []


def test_the_second_round_skips_the_judge_after_code_problems(session: Session) -> None:
    bad = Script.model_validate(GOOD).model_dump()
    bad["segments"][1]["turns"][1]["text"] = "Kevin Punter scored 21 points."
    llm = FakeLlm({Judgement: judge(), Script: lambda prompt: Script.model_validate(bad)})
    run = planned_run(session, llm)
    run.episode.script = bad

    with pytest.raises(StageFailed, match="failed twice") as failure:
        check_script(run)

    assert failure.value.details["rounds"][1]["judged"] is False
    assert [schema for schema, _ in llm.prompts] == [Judgement, Script]


def test_a_turn_the_judge_skips_is_a_problem(session: Session) -> None:
    def lazy_judge(prompt: str) -> Judgement:
        return Judgement.model_validate({"verdicts": []})

    llm = FakeLlm({Judgement: lazy_judge, Script: lambda prompt: Script.model_validate(GOOD)})
    run = planned_run(session, llm)
    run.episode.script = GOOD

    with pytest.raises(StageFailed) as failure:
        check_script(run)

    assert "did not review this turn" in failure.value.details["rounds"][0]["problems"][0]
