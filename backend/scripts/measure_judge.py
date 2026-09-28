"""Measure the real judge on 28 hand-labelled claims about real sources (D20).

Run from backend/:
    python scripts/measure_judge.py          # free: prompt size and cost estimate
    python scripts/measure_judge.py --run    # one paid gpt-6-luna call
"""

import argparse
import json
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import engine
from app.models import Article
from app.pipeline.checks import JUDGE_EFFORT, JUDGE_INSTRUCTIONS, Judgement, judge_prompt
from app.pipeline.llm import PRICES, OpenAILlm
from app.pipeline.script import (
    SPANISH_GLOSSARY,
    EpisodeSource,
    Script,
    context_text,
    episode_source,
)

SOURCES = {
    "S1": "https://acb.com/es/liga/noticias/el-real-madrid-suda-para-derrotar-a-un-gran-unicaja-89-87-146132",
    "S2": "https://acb.com/es/liga/noticias/batemon-y-mcghee-se-alian-para-conquistar-el-roig-arena-100-105-146131",
    "S3": "https://acb.com/es/liga/noticias/jassel-perez-acaba-con-la-resistencia-murciana-84-77-146128",
    "S4": "https://www.espn.com/nba/story/_/id/50030670/sources-warriors-curry-reach-2-year-extension-worth-116-million",
    "S5": "https://www.eurohoops.net/en/euroleague/2012892/the-nba-offer-for-a-joint-project-in-europe-is-on-the-euroleague-table/",
    "S6": "https://api-live.euroleague.net/v3/competitions/E/seasons/E2026/games/4/stats",
    "S7": "https://www.acb.com/es/calendario#round-2",
}
PLAN = {"selected_at": "2026-09-28T08:00:00+00:00", "coverage": "catch-up"}
ZONE = ZoneInfo("Europe/Madrid")

CLAIMS: list[tuple[str, list[str], str]] = [
    ("Real Madrid beat Unicaja 89–87 on Sunday 27 September.", ["S1", "CTX"], "pass"),
    ("Théo Maledon led Real Madrid with 17 points.", ["S1"], "pass"),
    ("Théo Maledon scored 23 points for Real Madrid.", ["S1"], "contradicted"),
    ("A 12–1 run in the final quarter sparked Real Madrid's comeback.", ["S1"], "pass"),
    ("Real Madrid cruised to an easy win over Unicaja.", ["S1"], "contradicted"),
    (
        (
            "Unicaja coach Txus Vidorreta knocked Real Madrid out of last season's playoffs "
            "with La Laguna Tenerife."
        ),
        ["S1"],
        "pass",
    ),
    ("Real Madrid were back at home for the first time in 113 days.", ["S1"], "pass"),
    (
        "iLERNA Lleida won 105–100 at Valencia Basket, with James Batemon scoring 23 points.",
        ["S2"],
        "pass",
    ),
    ("Darius McGhee hit 2 quick three-pointers early on.", ["S2"], "pass"),
    ("Darius McGhee recorded 2 triple-doubles.", ["S2"], "contradicted"),
    ("Lleida's James Batemon posted a PIR of 30.", ["S2"], "pass"),
    ("FIATC Girona beat UCAM Murcia 84–77, with Jassel Pérez scoring 20 points.", ["S3"], "pass"),
    ("Mac McClung is a three-time NBA dunk contest champion.", ["S3"], "pass"),
    ("UCAM Murcia shot 34% from the field.", ["S3"], "pass"),
    (
        "Stephen Curry has agreed to a 2-year, $116 million extension, league sources told ESPN.",
        ["S4"],
        "pass",
    ),
    ("The Warriors officially announced Stephen Curry's extension.", ["S4"], "overstated"),
    (
        "Eurohoops reports the NBA has sent the EuroLeague an offer for a possible collaboration.",
        ["S5"],
        "pass",
    ),
    ("The EuroLeague has accepted the NBA's offer for a joint league.", ["S5"], "unsupported"),
    ("The NBA has confirmed its offer to the EuroLeague.", ["S5"], "overstated"),
    ("FC Barcelona beat Anadolu Efes 89–82 at home on Thursday 24 September.", ["S6"], "pass"),
    ("Anadolu Efes beat FC Barcelona 89–82.", ["S6"], "misattributed"),
    ("FC Barcelona beat Anadolu Efes 89–82 on Friday 25 September.", ["S6"], "wrong_time"),
    ("Barça visit UCAM Murcia on Sunday 4 October.", ["S7", "CTX"], "pass"),
    ("Barça visit UCAM Murcia this Sunday.", ["S7", "CTX"], "pass"),
    ("Barça visited UCAM Murcia yesterday.", ["S7", "CTX"], "wrong_time"),
    (
        "Welcome to Daily Briefing: today we catch up on Barça, the EuroLeague and the NBA.",
        [],
        "pass",
    ),
    ("What a start for Barça!", [], "pass"),
    ("Barça have won all 7 of their LaLiga games.", [], "unsupported"),
]


def load_sources(session: Session) -> dict[str, EpisodeSource]:
    sources = {"CTX": EpisodeSource("CTX", "Episode context", "en", context_text(PLAN, ZONE), True)}
    for source_id, url in SOURCES.items():
        article = session.scalars(select(Article).where(Article.url == url)).one()
        sources[source_id] = episode_source(source_id, article, ZONE)
    return sources


def claims_script() -> Script:
    turns = [
        {"speaker": ("host", "analyst")[n % 2], "text": text, "source_ids": ids}
        for n, (text, ids, _) in enumerate(CLAIMS)
    ]
    return Script.model_validate(
        {"title": "Judge measurement", "segments": [{"key": "claims", "turns": turns}]}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="make the paid call")
    args = parser.parse_args()
    config = get_settings()
    instructions = JUDGE_INSTRUCTIONS.format(glossary=SPANISH_GLOSSARY)
    with Session(engine) as session:
        turn_ids, prompt = judge_prompt(claims_script(), load_sources(session))
    tokens = (len(instructions) + len(prompt)) / 4
    _, _, price_write, price_out = PRICES[config.openai_judge_model]
    estimate = (tokens * price_write + 4_000 * price_out) / 1_000_000
    print(f"{config.openai_judge_model}: ~{tokens:,.0f} input tokens, at most ~${estimate:.4f}")
    if not args.run:
        return
    llm = OpenAILlm(config.openai_api_key)
    judgement, call = llm.parse(
        model=config.openai_judge_model,
        instructions=instructions,
        prompt=prompt,
        schema=Judgement,
        effort=JUDGE_EFFORT,
    )
    verdicts = {verdict.turn: verdict for verdict in judgement.verdicts}
    rows, right, false_alarms, misses = [], 0, 0, 0
    for turn_id, (text, ids, expected) in zip(turn_ids, CLAIMS, strict=True):
        verdict = verdicts.get(turn_id)
        got = verdict.verdict if verdict else "missing"
        passed = got in ("supported", "opinion")
        should_pass = expected == "pass"
        right += passed == should_pass
        false_alarms += should_pass and not passed
        misses += not should_pass and passed
        rows.append(
            {
                "claim": text,
                "sources": ids,
                "expected": expected,
                "verdict": got,
                "explanation": verdict.explanation if verdict else "",
            }
        )
        print(f"{'OK ' if passed == should_pass else 'ERR'} {expected:>13} → {got:<13} {text}")
    print(
        f"\n{right}/{len(CLAIMS)} right · {false_alarms} false alarms · {misses} misses · "
        f"{call.input_tokens} in / {call.output_tokens} out · ${call.cost_usd:.4f} · "
        f"{call.latency_ms / 1000:.1f} s"
    )
    out = config.data_dir / "judge" / "measurement.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"call": call.__dict__, "rows": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
