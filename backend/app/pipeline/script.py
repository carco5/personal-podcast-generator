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
CHARS_PER_TURN = 115


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
    header = article.title if article.kind == "data" else f"{article.title}\nPublished: {published}"
    return EpisodeSource(
        source_id,
        f"{kind} · {SOURCE_NAMES.get(article.source, article.source)}",
        article.language,
        with_day_labels(f"{header}\n{article.body}", today),
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
  Monday"), welcomes the listener to {show} and introduces {host} and {analyst} by name;
  {analyst} says a short hello. Tease two or three stories; never list every section. The intro
  never compresses a record: say it with its scope ("the third-highest total in a league
  opener") or leave the figure out.
- Each section tells its lead story in depth through its angle and key facts, in about the
  number of turns the plan gives it; then its roundup, if any, in one line; then its next game,
  if the plan gives one. A brief section gets one short line.
- Tell a result with its score before commenting on it ("Barça won 3–1 at Sevilla"), then who
  decided it.
- Link each section to the conversation so far: its first turn picks up a thread from the plan,
  a contrast or the listener's team, then moves into the new story. Vary how sections open;
  never open two sections the same way (e.g. "In LaLiga…", "In the Champions League…").
- The switch from one sport to the other (football to basketball) gets one natural bridge line,
  through the club or the week. The closing gets a short lead-in ("Before we go…") before
  looking ahead.
- A bridge links content ("Barça's week wasn't only about football…"); it never describes the
  show's structure ("now we jump to…", "first, let's look at"). Never end a section by
  announcing the next one ("Now, LeBron in Philadelphia.").
- When the listener's team has a section per sport, name the team's side once at the start of
  that section ("Barça's basketball team"), and then just the team's name.
- A competition section follows its angle: what matters there to the listener's team. Never
  repeat what an earlier section told; refer back to it instead.
- Mention each upcoming game once in its section and once in the closing, no more.
- "closing": after its lead-in, what to watch next, starting with the nearest game of the
  listener's team, then a short sign-off with the show's name; {analyst} says goodbye too.
Each segment has a target length: aim for its characters and turns, within 10%. Reach it with the
plan's facts and your analysis of them: never pad and never invent.

Conversation:
- Tell facts the way a fan tells a friend, not the way a match report lists them. Use fans'
  vocabulary when the data supports it: "hat-trick" for three goals by one player, "brace" for
  two (the goal data labels them). Example: "Barça won 3–1 at Sevilla, and all 3 were Raphinha's:
  a hat-trick." instead of "Raphinha scored all 3 against Sevilla." Natural never means adding
  facts: no "stunning", "dominated" or "comeback" unless a source says it.
- Every turn answers, builds on or pushes back on the one before: if two turns could swap places
  without losing meaning, rewrite them.
- More back-and-forth inside each section: the analyst reacts to what the host just said before
  adding something new, and the host builds on the analyst's point instead of moving straight to
  the next fact. Never two fact-only turns in a row. Use callbacks to earlier moments in the
  episode when they fit.
- Each turn makes one point; don't stack unrelated facts in one turn.
- Mix short reactions (3 to 8 words) with explanations of one to three sentences. At most two
  numbers per turn; a score counts as one. Use only stats that make a point; never read out a
  stat line ("1 rebound and 1 assist").
- The host asks at most one or two questions per section, never one the host obviously knows the
  answer to; the host's other turns react, add a fact or push back. Sometimes {analyst} asks
  {host}. Each host says the other's name at most twice in the episode, besides the intro.
- {analyst} takes clear positions, like a fan who knows the game, with at most one hedge in the
  whole episode ("it's early", "only one game"). One or two moments of mild disagreement.
- Opinions, reactions, feelings and predictions are welcome, but they never add facts.
- At most two stock openers in the whole episode ("Absolutely", "Exactly", "Great point",
  "You're spot on") and at most three light spoken markers ("I mean", "honestly", "look").
- Use the names fans use ("PSG", "Atlético", "Madrid", "Barça"), never abbreviations from the
  data ("Man Utd"). Keep the sport clear: never shorten a club's name to one that could mean a
  club in the other sport ("Paris Basketball", never just "Paris"). Name the players whenever the
  sources do.

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


def target(chars: int) -> str:
    return f"about {chars} characters, about {max(1, round(chars / CHARS_PER_TURN))} turns"


def cited(fact: dict) -> str:
    return f"{fact['text']} (sources {', '.join(fact['source_ids'])})"


def prompt(run: Run, sources: dict[str, EpisodeSource]) -> str:
    plan = run.episode.plan
    editorial = plan["editorial"]
    used: set[str] = set(editorial["hook"]["source_ids"])
    lines = [f"[CTX] {sources['CTX'].text}", "", "PLAN", f"Hook: {cited(editorial['hook'])}"]
    lines.append(f'- Segment "intro": {target(plan["intro_chars"])}.')
    blocks = {block["key"]: block for block in plan["blocks"]}
    for section in editorial["sections"]:
        block = blocks[section["key"]]
        lines.append(f'- Segment "{block["key"]}" ({block["title"]}): {target(block["chars"])}.')
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
    lines.append(f'- Segment "closing": {target(plan["closing_chars"])}.')
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
