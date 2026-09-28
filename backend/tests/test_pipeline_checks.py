import copy

import pytest

from app.pipeline.checks import code_problems, source_numbers
from app.pipeline.script import EpisodeSource, Script

PLAN = {
    "selected_at": "2026-10-01T08:00:00+00:00",
    "today": "Thursday 1 October 2026",
    "coverage": "catch-up: the listener's first episode",
    "target_chars": 3720,
    "intro_chars": 300,
    "closing_chars": 250,
    "blocks": [
        {
            "key": "euroleague",
            "title": "EuroLeague",
            "weight": "high",
            "sport": "basketball",
            "chars": 760,
            "stories": [{"source_ids": ["S1"], "reason": ""}, {"source_ids": ["S2"], "reason": ""}],
            "context_ids": ["S3"],
        }
    ],
}
SOURCES = {
    "CTX": EpisodeSource("CTX", "Episode context", "en", "Today is Thursday 1 October 2026.", True),
    "S1": EpisodeSource(
        "S1",
        "Official data · EuroLeague",
        "en",
        "EuroLeague Round 2, Tuesday 29 September 2026: FC Barcelona beat Dubai 80–70 away, "
        "winning by 10 points. Kevin Punter (FC Barcelona): 19 points, 3 rebounds.",
        True,
    ),
    "S2": EpisodeSource(
        "S2",
        "Official · Liga ACB",
        "es",
        "El Real Madrid suda para derrotar a un gran Unicaja (89-87)\nPublished: Sunday 27 "
        "September 2026\nLa jornada dejó 94,8 puntos por partido ante 1.706 espectadores.",
        False,
    ),
    "S3": EpisodeSource(
        "S3",
        "Official data · EuroLeague",
        "en",
        "EuroLeague Round 3 fixtures. Friday 2 October 2026: Besiktas host FC Barcelona.",
        True,
    ),
}


def turn(speaker: str, text: str, *source_ids: str) -> dict:
    return {"speaker": speaker, "text": text, "source_ids": list(source_ids)}


GOOD = {
    "title": "Barça win in Dubai",
    "segments": [
        {
            "key": "intro",
            "turns": [
                turn("host", "Barça won 80–70 in Dubai on Tuesday.", "S1"),
                turn("analyst", "What a start to the week!"),
            ],
        },
        {
            "key": "euroleague",
            "turns": [
                turn("host", "FC Barcelona beat Dubai 80–70 away.", "S1"),
                turn("analyst", "[excited] Kevin Punter scored 19 points.", "S1"),
                turn("host", "In Spain, Real Madrid edged Unicaja 89–87.", "S2"),
                turn("analyst", "The round averaged 94.8 points, with 1,706 fans watching.", "S2"),
                turn("host", "Next, Barça visit Besiktas on Friday 2 October.", "S3"),
            ],
        },
        {"key": "closing", "turns": [turn("host", "That's all for today. See you tomorrow!")]},
    ],
}


def problems_after(
    segment: int, number: int, text: str, source_ids: list[str] | None = None
) -> list[str]:
    script = copy.deepcopy(GOOD)
    script["segments"][segment]["turns"][number]["text"] = text
    if source_ids is not None:
        script["segments"][segment]["turns"][number]["source_ids"] = source_ids
    return code_problems(Script.model_validate(script), PLAN, SOURCES)


def test_the_good_script_passes() -> None:
    assert code_problems(Script.model_validate(GOOD), PLAN, SOURCES) == []


@pytest.mark.parametrize(
    ("segment", "number", "text", "expected"),
    [
        (1, 1, "[excited] Kevin Punter scored 21 points.", "numbers ['21'] are not in"),
        (1, 0, "FC Barcelona beat Dubai 70–80 away.", "must be written winner first"),
        (1, 0, "FC Barcelona beat Dubai 80–19 away.", "the score 80–19 is not in"),
        (1, 1, "Kevin Punter scored nineteen points.", '"nineteen points" must use digits'),
        (1, 1, "[whispers] Kevin Punter scored 19 points.", "[whispers] is not an allowed"),
        (2, 0, "Read more at www.espn.com today.", "contains a URL"),
        (2, 0, "That's **all** for today.", "contains markdown"),
        (2, 0, "That's all for today 🏀", "contains an emoji"),
        (2, 0, "That's all from S1 and S2 today.", "says a source id aloud"),
        (2, 0, "That's all for today. " * 25, "keep turns under 500"),
    ],
)
def test_each_check_catches_its_sabotage(
    segment: int, number: int, text: str, expected: str
) -> None:
    problems = problems_after(segment, number, text)

    assert any(expected in problem for problem in problems), problems


def test_unknown_source_ids_are_caught() -> None:
    problems = problems_after(1, 0, "FC Barcelona beat Dubai 80–70 away.", ["S9"])

    assert any("cites ['S9']" in problem for problem in problems)


def test_a_number_without_sources_is_caught() -> None:
    problems = problems_after(1, 0, "FC Barcelona won by 10 points.", [])

    assert any("numbers ['10']" in problem for problem in problems)


def test_spanish_numbers_are_normalised() -> None:
    wrong = "The round averaged 94.8 points, with 1.706 fans watching."

    assert any("['1.706']" in problem for problem in problems_after(1, 3, wrong))


def test_numbers_written_in_words_in_a_source() -> None:
    spanish = (
        "Pérez sumó nueve rebotes, veintidós puntos en la primera parte y treinta y dos en total."
    )
    english = "He signed a two-year deal once, after twenty-one games and one great season."

    assert {"9", "22", "32"} <= source_numbers(spanish, "es")
    assert {"2", "21"} <= source_numbers(english, "en")
    assert not {"1", "11"} & source_numbers(english, "en")
    assert "1" not in source_numbers("Cogió un rebote y fue uno de los mejores.", "es")


def test_the_script_must_still_use_digits() -> None:
    problems = problems_after(1, 1, "Kevin Punter grabbed nine rebounds.")

    assert any('"nine rebounds" must use digits' in problem for problem in problems)


def test_structure_checks() -> None:
    no_lead = copy.deepcopy(GOOD)
    no_lead["segments"][0]["turns"][0]["source_ids"] = []
    no_lead["segments"][0]["turns"][0]["text"] = "Big night in the EuroLeague."
    assert any(
        "lead story" in p for p in code_problems(Script.model_validate(no_lead), PLAN, SOURCES)
    )

    skipped = copy.deepcopy(GOOD)
    del skipped["segments"][1]["turns"][2:4]
    assert any(
        "story 2 (['S2']) is not covered" in p
        for p in code_problems(Script.model_validate(skipped), PLAN, SOURCES)
    )

    reordered = copy.deepcopy(GOOD)
    reordered["segments"].reverse()
    assert (
        "segments must be exactly"
        in code_problems(Script.model_validate(reordered), PLAN, SOURCES)[0]
    )

    tagged = copy.deepcopy(GOOD)
    tagged["segments"][2]["turns"] = [turn("host", "[laughs] Bye!")] * 7
    assert any(
        "8 audio tags" in p for p in code_problems(Script.model_validate(tagged), PLAN, SOURCES)
    )

    long = copy.deepcopy(GOOD)
    long["segments"][2]["turns"] = [turn("host", "See you tomorrow, everyone. " * 15)] * 6
    assert any(
        "the plan allows about 1310" in p
        for p in code_problems(Script.model_validate(long), PLAN, SOURCES)
    )
