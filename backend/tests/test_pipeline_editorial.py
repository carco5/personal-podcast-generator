from app.pipeline.editorial import (
    BRIEF_CHARS,
    EditorialPlan,
    budget_shares,
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
            "next_up": None,
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
        laliga={"roundup_ids": ["S5"], "next_up": {"text": "Next.", "source_ids": ["S1"]}},
        nba={"key_facts": [fact] * 6},
    )
    broken.hook.source_ids = ["S99"]

    problems = plan_problems(broken, PLAN, KNOWN)

    assert "barca: lead_ids must be source ids of its stories." in problems
    assert any(p.startswith("laliga: roundup_ids") for p in problems)
    assert "laliga: next_up must cite this section's context." in problems
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
                    "next_up": None,
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
