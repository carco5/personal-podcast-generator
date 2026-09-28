from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import select

from app.models import Article, EpisodeArticle, Language
from app.pipeline.common import Run
from app.pipeline.days import with_day_labels
from app.sources.base import spoken_date
from app.sources.registry import SOURCE_NAMES

ALLOWED_TAGS = ("excited", "laughs", "curious", "sarcastic")
MAX_TAGS = 8
MAX_WRITE_CHARS = 3_000
WRITE_EFFORT = "low"


class Turn(BaseModel):
    speaker: Literal["host", "analyst"]
    text: str
    source_ids: list[str]


class Segment(BaseModel):
    key: str
    turns: list[Turn]


class Script(BaseModel):
    title: str
    segments: list[Segment]


@dataclass(frozen=True)
class EpisodeSource:
    source_id: str
    label: str
    language: Language
    text: str
    is_data: bool


def episode_day(plan: dict, zone: ZoneInfo) -> date:
    return datetime.fromisoformat(plan["selected_at"]).astimezone(zone).date()


def context_text(plan: dict, zone: ZoneInfo) -> str:
    today = episode_day(plan, zone)
    return with_day_labels(
        f"Today is {spoken_date(today)}. This episode is {plan['coverage']}.", today
    )


def script_sources(run: Run) -> dict[str, EpisodeSource]:
    rows = run.session.execute(
        select(EpisodeArticle.source_id, Article)
        .join(Article, Article.id == EpisodeArticle.article_id)
        .where(EpisodeArticle.episode_id == run.episode.id)
    ).all()
    zone = ZoneInfo(run.podcast.timezone)
    today = episode_day(run.episode.plan, zone)
    sources = {
        "CTX": EpisodeSource(
            "CTX", "Episode context", "en", context_text(run.episode.plan, zone), True
        )
    }
    for source_id, article in sorted(rows, key=lambda row: int(row[0][1:])):
        sources[source_id] = episode_source(source_id, article, zone, today)
    return sources


def episode_source(source_id: str, article: Article, zone: ZoneInfo, today: date) -> EpisodeSource:
    if article.kind == "data":
        kind = "Official data"
    else:
        kind = "Official" if article.official else "Outlet"
    published = spoken_date(article.published_at.astimezone(zone).date())
    return EpisodeSource(
        source_id,
        f"{kind} · {SOURCE_NAMES.get(article.source, article.source)}",
        article.language,
        with_day_labels(f"{article.title}\nPublished: {published}\n{article.body}", today),
        article.kind == "data",
    )


INSTRUCTIONS = """\
You write the script of "{show}", a personal sports podcast: a real conversation between two
hosts who are fans of what the listener follows.
- {host} (speaker "host") drives the show: sets up each story, asks {analyst} real questions and
  keeps the pace.
- {analyst} (speaker "analyst") explains why it matters: context, comparisons, streaks, standout
  players and opinions. The analyst never reads out lists of results.
Their personalities, from the listener's settings (style only, never a source of facts):
- {host}: {host_personality}
- {analyst}: {analyst_personality}
Tone: {tone}.

Write from the PLAN: exactly its segments, in its order, with their keys, and only what it gives.
- "intro": {host} opens with the plan's hook in one sentence, says which day it is ("It's
  Monday"), welcomes the listener to {show} and introduces {host} and {analyst} by name. Tease
  two or three stories; never list every section.
- Each section tells its lead story in depth, in 3 to 5 turns, through its angle and key facts;
  then its roundup, if any, in one line; then what comes next. A brief section gets one short
  line.
- When the listener's team has a section per sport, name the team's side once at the start of
  that section ("Barça's basketball team"), and then just the team's name.
- A competition section follows its angle: what matters there to the listener's team. Never
  repeat what an earlier section told; refer back to it instead.
- Bridge sections with the plan's threads when one fits; otherwise with a short, plain handoff.
  No pun-based transitions. The move from one sport to the other is the biggest jump: make it
  clear and smooth.
- "closing": what to watch next, starting with the nearest game of the listener's team, then a
  short sign-off with the show's name.
Each segment has a target length in characters: aim for it, within 10%. Reach it with the plan's
facts and your analysis of them: never pad and never invent.

Conversation:
- Every turn answers, builds on or pushes back on the one before: if two turns could swap places
  without losing meaning, rewrite them.
- Mix short reactions (3 to 8 words) with explanations of one to three sentences. At most two
  numbers per turn; a score counts as one.
- In each section the host asks at least one genuine question, never one the host obviously
  knows the answer to.
- One or two moments of mild disagreement in the episode.
- Opinions, reactions, feelings and predictions are welcome, but they never add facts.
- At most two stock openers in the whole episode ("Absolutely", "Exactly", "Great point",
  "You're spot on") and at most three light spoken markers ("I mean", "honestly", "look").
- Use the names fans use ("PSG", "Atlético", "Madrid", "Barça"), never abbreviations from the
  data ("S. Bratislava", "Man Utd"). Name the players whenever the sources do.

Facts:
- Use only facts from the sources. A turn that states any fact lists the ids of its sources in
  source_ids, including the context sources (standings, fixtures) that a number or a day comes
  from. A turn with an empty list may only react, give an opinion or link two stories.
- Every name, number, result, quote, day, or description of how a game went ("dominated", "late
  winner", "came from behind") must come from a cited source.
- Never compute numbers: no margins, totals or percentages unless a source states them (the
  standings state each team's gap to the leader).
- Keep the source's certainty: rumours stay rumours ("reportedly", "according to ESPN").
- Name the right team and player for every fact.
- Days: never say a full date. Say a day as its source labels it ([say: last Saturday], [say:
  Saturday the 10th]), or with context from the sources ("before the international break").
- Sources in Spanish: translate faithfully. {glossary}

Numbers: digits for every quantity from the sources ("20 points", "3 wins"), English format
("81.5", "1,706"). Ordinals in words ("first place"). Scores winner first with an en dash
("89–82"). Records in words with digits ("3 wins and 1 loss"), never as a dash pair.

Voice: about one audio tag every four or five turns (never more than {max_tags} in the whole
script), varied, only where the line carries that emotion; only {tags}, at the start of a turn.
No other brackets, no markdown, no URLs, no emojis and no source ids in the spoken text.

Title: a short episode title (at most 60 characters) that names the lead story.
"""

SPANISH_GLOSSARY = (
    'In Liga ACB reports, "pt" or "puntos" are points; "val" or "valoración" is the performance '
    'rating (PIR), not points: say "a performance rating of 30"; "rebotes" are rebounds, '
    '"asistencias" assists and "tapones" blocks; a '
    '"triple" is a three-pointer (not a triple-double), but "triple campeón" means three-time '
    'champion; a "parcial" is a scoring run, not a final '
    'score; "prórroga" is overtime and a "2+1" is an and-one. Decimal commas become points '
    '("94,8" is 94.8).'
)

TONES = {
    "casual": "relaxed and friendly, like two friends who follow the sport closely",
    "analytical": "focused on what the results and numbers mean, still conversational",
}


def instructions(run: Run) -> str:
    host, analyst = run.podcast.hosts
    return INSTRUCTIONS.format(
        show=run.podcast.show_name,
        host=host["name"],
        analyst=analyst["name"],
        host_personality=host["personality"],
        analyst_personality=analyst["personality"],
        tone=TONES[run.podcast.tone],
        max_tags=MAX_TAGS,
        tags=", ".join(f"[{tag}]" for tag in ALLOWED_TAGS),
        glossary=SPANISH_GLOSSARY,
    )


def cited(fact: dict) -> str:
    return f"{fact['text']} (sources {', '.join(fact['source_ids'])})"


def prompt(run: Run, sources: dict[str, EpisodeSource]) -> str:
    plan = run.episode.plan
    editorial = plan["editorial"]
    used: set[str] = set(editorial["hook"]["source_ids"])
    lines = [f"[CTX] {sources['CTX'].text}", "", "PLAN", f"Hook: {cited(editorial['hook'])}"]
    lines.append(f'- Segment "intro": about {plan["intro_chars"]} characters.')
    blocks = {block["key"]: block for block in plan["blocks"]}
    for section in editorial["sections"]:
        block = blocks[section["key"]]
        lines.append(
            f'- Segment "{block["key"]}" ({block["title"]}): about {block["chars"]} characters.'
        )
        if section["brief"]:
            lines.append("  Brief: one short line.")
        if section["major"]:
            lines.append("  Major story: give it room.")
        lines.append(f"  Angle: {section['angle']}")
        lines.append("  Lead facts:")
        for fact in section["key_facts"]:
            lines.append(f"    - {cited(fact)}")
            used |= set(fact["source_ids"])
        if section["roundup_ids"]:
            lines.append(f"  Roundup: {', '.join(section['roundup_ids'])}")
            used |= set(section["roundup_ids"])
        if section["next_up"]:
            lines.append(f"  Next up: {cited(section['next_up'])}")
            used |= set(section["next_up"]["source_ids"])
    lines.append(f'- Segment "closing": about {plan["closing_chars"]} characters.')
    if editorial["threads"]:
        lines.append("Threads:")
        for thread in editorial["threads"]:
            lines.append(f"- {thread['from_key']} → {thread['to_key']}: {cited(thread['link'])}")
            used |= set(thread["link"]["source_ids"])
    lines += ["", "SOURCES"]
    for source in sources.values():
        if source.source_id in used and source.source_id != "CTX":
            text = source.text if source.is_data else source.text[:MAX_WRITE_CHARS]
            lines += ["", f"[{source.source_id}] {source.label}", text]
    return "\n".join(lines)


def write_script(run: Run, problems: list[str] | None = None) -> dict:
    sources = script_sources(run)
    text = prompt(run, sources)
    if problems:
        text += (
            "\n\nYOUR PREVIOUS SCRIPT\n"
            + Script.model_validate(run.episode.script).model_dump_json()
            + "\n\nIt failed these checks:\n"
            + "\n".join(f"- {problem}" for problem in problems)
            + "\nReturn the full corrected script. Fix every problem and keep what was right."
        )
    script, call = run.llm.parse(
        model=run.config.openai_write_model,
        instructions=instructions(run),
        prompt=text,
        schema=Script,
        effort=WRITE_EFFORT,
    )
    run.calls.append(call)
    run.episode.script = script.model_dump()
    run.episode.title = script.title
    run.session.flush()
    return {
        "rewrite": bool(problems),
        "segments": len(script.segments),
        "turns": sum(len(segment.turns) for segment in script.segments),
        "characters": sum(len(t.text) for s in script.segments for t in s.turns),
    }
