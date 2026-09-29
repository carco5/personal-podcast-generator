from datetime import date

from app.pipeline.editorial import (
    BRIEF_CHARS,
    INSTRUCTIONS,
    EditorialPlan,
    budget_shares,
    next_games,
    plan_problems,
)

PLAN = {
    "target_chars": 3720,
    "intro_chars": 300,
    "closing_chars": 250,
    "blocks": [
        {
            "key": "barca",
            "weight": "high",
            "stories": [{"source_ids": ["S1", "S2"]}, {"source_ids": ["S3"]}],
            "context_ids": [],
        },
        {
            "key": "laliga",
            "weight": "medium",
            "stories": [{"source_ids": ["S5"]}, {"source_ids": ["S6"]}],
            "context_ids": ["S4"],
        },
        {"key": "nba", "weight": "low", "stories": [{"source_ids": ["S7"]}], "context_ids": []},
    ],
}
KNOWN = {"CTX", "S1", "S2", "S3", "S4", "S5", "S6", "S7"}


def editorial(**changes: dict) -> EditorialPlan:
    sections = []
    for block in PLAN["blocks"]:
        section = {
            "key": block["key"],
            "lead_ids": block["stories"][0]["source_ids"],
            "angle": "Why it matters.",
            "key_facts": [{"text": "A fact.", "source_ids": block["stories"][0]["source_ids"]}],
            "roundup_ids": [],
            "brief": False,
            "major": False,
        }
        section.update(changes.get(block["key"], {}))
        sections.append(section)
    return EditorialPlan.model_validate(
        {"hook": {"text": "Hook.", "source_ids": ["S1"]}, "sections": sections, "threads": []}
    )


def test_shares_follow_the_weights_and_sum_to_the_body() -> None:
    shares = budget_shares(PLAN, editorial())

    assert sum(shares.values()) == 3170
    assert shares == {"barca": 1585, "laliga": 1057, "nba": 528}


def test_brief_and_major_sections_change_the_shares() -> None:
    shares = budget_shares(PLAN, editorial(laliga={"major": True}, nba={"brief": True}))

    assert shares["nba"] == BRIEF_CHARS
    assert shares["barca"] == shares["laliga"] == (3170 - BRIEF_CHARS) // 2
    assert sum(shares.values()) == 3170


def test_a_valid_plan_has_no_problems() -> None:
    assert plan_problems(editorial(), PLAN, KNOWN) == []


def test_each_plan_rule_catches_its_sabotage() -> None:
    fact = {"text": "A fact.", "source_ids": ["S5"]}
    broken = editorial(
        barca={"lead_ids": ["S5"], "key_facts": [{"text": "LaLiga fact.", "source_ids": ["S5"]}]},
        laliga={"roundup_ids": ["S5"]},
        nba={"key_facts": [fact] * 6},
    )
    broken.hook.source_ids = ["S99"]

    problems = plan_problems(broken, PLAN, KNOWN)

    assert "barca: lead_ids must be source ids of its stories." in problems
    assert any(p.startswith("laliga: roundup_ids") for p in problems)
    assert "nba: give 1 to 3 key facts." in problems
    assert "hook must cite sources of this episode." in problems


def test_a_fact_with_a_stat_line_is_rejected_and_major_allows_more_facts() -> None:
    stat_line = {
        "text": "Bacon had 24 points, five rebounds, four assists and a PIR of 31.",
        "source_ids": ["S1"],
    }
    fact = {"text": "A fact.", "source_ids": ["S1"]}
    problems = plan_problems(editorial(barca={"key_facts": [stat_line]}), PLAN, KNOWN)
    assert any("has more than 2 numbers" in p for p in problems)

    major = editorial(barca={"major": True, "key_facts": [fact] * 5})
    assert plan_problems(major, PLAN, KNOWN) == []


def test_a_grouped_story_can_be_split_into_lead_and_roundup() -> None:
    grouped = {
        **PLAN,
        "blocks": [
            {
                "key": "euroleague",
                "weight": "medium",
                "stories": [{"source_ids": ["S1", "S2", "S3"]}],
                "context_ids": [],
            }
        ],
    }
    answer = EditorialPlan.model_validate(
        {
            "hook": {"text": "Hook.", "source_ids": ["S1"]},
            "sections": [
                {
                    "key": "euroleague",
                    "lead_ids": ["S1"],
                    "angle": "Why.",
                    "key_facts": [{"text": "A fact.", "source_ids": ["S1"]}],
                    "roundup_ids": ["S2", "S3"],
                    "brief": False,
                    "major": False,
                }
            ],
            "threads": [],
        }
    )

    assert plan_problems(answer, grouped, KNOWN) == []


def test_sections_must_match_the_plan() -> None:
    swapped = editorial()
    swapped.sections.reverse()

    assert plan_problems(swapped, PLAN, KNOWN) == [
        "The sections must be exactly ['barca', 'laliga', 'nba'], in that order."
    ]


TEAM = frozenset({"FC Barcelona", "Barça", "Barcelona"})
MONDAY = date(2026, 9, 28)
SAMPLE = {
    "blocks": [
        {
            "key": "fc-barcelona-football",
            "interest": "fc-barcelona",
            "context_ids": ["S5", "S6", "S7", "S8"],
        },
        {"key": "laliga", "interest": "laliga", "context_ids": ["S6", "S8"]},
        {"key": "champions-league", "interest": "champions-league", "context_ids": ["S5", "S7"]},
        {"key": "nba", "interest": "nba", "context_ids": []},
    ]
}
METAS = {
    "S5": {"type": "standings", "teams": ["PSG", "Barcelona", "Liverpool"]},
    "S6": {"type": "standings", "teams": ["FC Barcelona", "Atlético de Madrid", "Real Betis"]},
    "S7": {
        "type": "fixtures",
        "games": [
            {"date": "2026-10-13", "home": "Lens", "away": "Sporting CP"},
            {"date": "2026-10-13", "home": "Galatasaray", "away": "Barcelona"},
        ],
    },
    "S8": {
        "type": "fixtures",
        "games": [
            {"date": "2026-10-09", "home": "Málaga CF", "away": "RCD Espanyol"},
            {"date": "2026-10-10", "home": "FC Barcelona", "away": "Getafe CF"},
        ],
    },
}


def test_next_up_is_the_team_game_given_once() -> None:
    upcoming = next_games(SAMPLE, METAS, TEAM, MONDAY)

    football = upcoming["fc-barcelona-football"]
    assert football is not None and football.source_ids == ["S8"]
    assert football.text == (
        "FC Barcelona host Getafe CF on Saturday 10 October 2026 [say: Saturday the 10th]."
    )
    assert upcoming["laliga"] is None
    champions = upcoming["champions-league"]
    assert champions is not None and champions.text.startswith("Galatasaray host Barcelona")
    assert upcoming["nba"] is None


def test_without_a_team_game_next_up_is_a_direct_rival() -> None:
    metas = {
        "S6": {
            "type": "standings",
            "teams": ["Atlético de Madrid", "FC Barcelona", "Real Betis", "Girona FC"],
        },
        "S9": {
            "type": "fixtures",
            "games": [
                {"date": "2026-10-10", "home": "Girona FC", "away": "Villarreal CF"},
                {"date": "2026-10-11", "home": "Real Betis", "away": "Sevilla FC"},
            ],
        },
    }
    plan = {
        "blocks": [
            {
                "key": "fc-barcelona-football",
                "interest": "fc-barcelona",
                "context_ids": ["S6", "S9"],
            },
            {"key": "laliga", "interest": "laliga", "context_ids": ["S6", "S9"]},
        ]
    }

    upcoming = next_games(plan, metas, TEAM, MONDAY)

    assert upcoming["fc-barcelona-football"] is None
    laliga = upcoming["laliga"]
    assert laliga is not None and laliga.text.startswith("Real Betis host Sevilla FC")


def test_without_a_team_there_is_no_next_up() -> None:
    upcoming = next_games(SAMPLE, METAS, frozenset(), MONDAY)

    assert set(upcoming.values()) == {None}


def test_the_editor_keeps_the_scope_of_a_record() -> None:
    assert "keeps its scope" in INSTRUCTIONS
