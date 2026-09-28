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
MAX_TAGS = 6
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
You write the script of "{show}", a personal daily sports podcast with two hosts.
- {host} (speaker "host") leads: introduces each story and gives the key facts.
- {analyst} (speaker "analyst") adds context, an opinion or a question.
Their personalities, from the listener's settings (style only, never a source of facts):
- {host}: {host_personality}
- {analyst}: {analyst_personality}
Tone: {tone}.

Structure: write exactly the segments listed in the plan, in that order, with their keys.
- "intro": open with a one-sentence hook on the lead story (the first story of the first block),
  citing its sources. Leave its details to its segment, which comes right after, and never repeat
  a sentence. Then welcome the listener to {show} and say what is in today's episode, in order.
- One segment per block: cover every story listed for it, in order. A story with several
  results is a roundup: one short sentence per result, shared between the two hosts. Give a day
  once for the results played on it and vary the wording (never "that day" twice). End the block
  with what comes next when its context has fixtures, but mention each fixture only once in the
  whole episode.
- The blocks are grouped by sport, in the order given. Say clearly when the episode moves to
  another sport ("Now, basketball."). When a club has a segment per sport, make clear which of
  its teams you mean ("Barça's football team", "Barça's basketball side").
- "closing": a short recap and a sign-off.
Each segment has a target length in characters: aim for it, within 10%. Reach it with facts,
context and analysis from the sources. Write less only when a story's sources run out: never pad
and never invent.

Write for the ear: sentences under 20 words, one idea and at most one number per sentence,
contractions. Introduce people by their team ("Barça's Kevin Punter"), or by a role only when a
source states it. Say team names in full, as fans say them ("Slovan Bratislava", "Borussia
Dortmund", "Manchester United"), never abbreviated forms from the data ("S. Bratislava", "Man
Utd"). Keep turns to one to three sentences and alternate the two voices.

Facts:
- Use only facts from the sources. A turn that states any fact lists the ids of its sources in
  source_ids, including the context sources (standings, fixtures) that a number or a date comes
  from. A turn with an empty list may only react, give an opinion or link two stories.
- Never compute numbers: no margins, totals or percentages unless a source states them.
- Keep the source's certainty: rumours stay rumours ("reportedly", "according to ESPN").
- Name the right team and player for every fact. Place events on the right day: for games and
  fixtures give the weekday with its date ("on Sunday 4 October"), from the sources or from
  [CTX], which lists the dates of the days around today.
- Sources in Spanish: translate faithfully. {glossary}

Numbers: digits for every quantity from the sources ("20 points", "3 wins"), English format
("81.5", "1,706"). Ordinals in words ("first place"). Scores winner first with an en dash
("89–82"). Records in words with digits ("3 wins and 1 loss"), never as a dash pair.

Voice: use 2 to 4 audio tags in the whole script where they fit the moment (never more than
{max_tags}), only {tags}, at the start of a turn.
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


def prompt(run: Run, sources: dict[str, EpisodeSource]) -> str:
    plan = run.episode.plan
    lines = [f"[CTX] {sources['CTX'].text}", "", "PLAN"]
    lines.append(f'- Segment "intro": about {plan["intro_chars"]} characters.')
    for block in plan["blocks"]:
        sport = block.get("sport") or "other"
        lines.append(
            f'- Segment "{block["key"]}" ({block["title"]}; sport: {sport}): '
            f"about {block['chars']} characters."
        )
        for number, story in enumerate(block["stories"], start=1):
            lines.append(f"  - Story {number}: sources {', '.join(story['source_ids'])}")
        if block["context_ids"]:
            lines.append(f"  - Context: {', '.join(block['context_ids'])}")
    lines.append(f'- Segment "closing": about {plan["closing_chars"]} characters.')
    lines += ["", "SOURCES"]
    for source in sources.values():
        if source.source_id != "CTX":
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
