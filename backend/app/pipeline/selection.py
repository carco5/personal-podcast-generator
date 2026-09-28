import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import delete, select

from app.catalog import CATALOG
from app.models import Article, Episode, EpisodeArticle, Interest
from app.pipeline.common import EpisodeSkipped, Run
from app.pipeline.fetch import episode_sources
from app.sources.base import spoken_date
from app.sources.registry import SPORTS, TOPIC_FEEDS, Sport, TopicFeed, source_sport

CHARS_PER_SECOND = 12.4
INTRO_CHARS = 300
CLOSING_CHARS = 250
STORY_CHARS = 380
NEWS_WINDOW = timedelta(days=3)
WEIGHT_POINTS = {"high": 3, "medium": 2, "low": 1}
PREVIEW_CHARS = 300
MAX_CANDIDATES = 25
SELECT_EFFORT = "low"


@dataclass
class Block:
    key: str
    title: str
    weight: str
    sport: Sport | None = None
    stories: list[Article] = field(default_factory=list)
    context: list[Article] = field(default_factory=list)
    wanted: int = 0
    interest: str = ""

    def __post_init__(self) -> None:
        self.interest = self.interest or self.key


class PickedStory(BaseModel):
    source_ids: list[str]
    reason: str


class PickedBlock(BaseModel):
    key: str
    stories: list[PickedStory]


class Picks(BaseModel):
    blocks: list[PickedBlock]


INSTRUCTIONS = """\
You are the news editor of a personal daily sports podcast. The listener's interests are given as
blocks, in order of priority, each with its candidate sources.

For each block, choose the stories that matter most to a fan of that interest: at most the number
given, most important first.
- A story is one event. When several candidates cover the same event (a game's official result
  and its report, or the same news from two outlets), put all their ids in that story's
  source_ids, the official one first.
- Less important results of the same round can share one roundup story: put up to 4 of them
  in its source_ids. Keep the most important games as stories of their own.
- In a block about one club, the first story is the club's latest results: put its latest
  result in each competition (league, European cup) together in that story, most recent first.
  Its news come after.
- Prefer substantial, fresh stories: results, signings, injuries, milestones, key statements.
- Skip previews of games that have already been played, promotional items and trivia.
- Use only the ids listed in that block, each id at most once.
- Give a one-sentence reason for each story.
"""


def select_stories(run: Run) -> dict:
    zone = ZoneInfo(run.podcast.timezone)
    since = previous_selection(run)
    told = told_articles(run)
    pool = run.session.scalars(
        select(Article).where(Article.source.in_(episode_sources(run)))
    ).all()
    pool, told = unique_articles(list(pool), told)
    blocks = build_blocks(run.interests, pool, since, run.now, told)
    allocate(blocks, story_slots(run.podcast.length_minutes))
    blocks = sport_order([block for block in blocks if block.wanted > 0])
    if not blocks:
        since_text = f" since {spoken_date(since.astimezone(zone).date())}" if since else ""
        raise EpisodeSkipped(f"No fresh news for your interests{since_text}.")
    picks = pick_stories(run, blocks)
    plan = save_plan(run, blocks, picks, since, zone)
    return {
        "coverage": plan["coverage"],
        "blocks": [
            {"key": b.key, "candidates": len(b.stories), "wanted": b.wanted} for b in blocks
        ],
        "stories": sum(len(block["stories"]) for block in plan["blocks"]),
    }


def previous_selection(run: Run) -> datetime | None:
    plan = run.session.scalar(
        select(Episode.plan)
        .where(
            Episode.user_id == run.episode.user_id,
            Episode.status == "completed",
            Episode.id != run.episode.id,
        )
        .order_by(Episode.finished_at.desc())
        .limit(1)
    )
    return datetime.fromisoformat(plan["selected_at"]) if plan else None


def unique_articles(pool: list[Article], told: set[int]) -> tuple[list[Article], set[int]]:
    groups: dict[tuple[str, str], list[Article]] = {}
    for article in pool:
        groups.setdefault((article.source, content_hash(article.body)), []).append(article)
    keep: set[int] = set()
    told_out = set(told)
    for copies in groups.values():
        newest = max(copies, key=lambda article: article.fetched_at)
        keep.add(newest.id)
        if any(article.id in told for article in copies):
            told_out.add(newest.id)
    return [article for article in pool if article.id in keep], told_out


def content_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def told_articles(run: Run) -> set[int]:
    return set(
        run.session.scalars(
            select(EpisodeArticle.article_id)
            .join(Episode, Episode.id == EpisodeArticle.episode_id)
            .where(Episode.user_id == run.episode.user_id, Episode.status == "completed")
        )
    )


def build_blocks(
    interests: list[Interest],
    pool: list[Article],
    since: datetime | None,
    now: datetime,
    told: set[int],
) -> list[Block]:
    ordered = sorted(interests, key=lambda i: (-WEIGHT_POINTS[i.weight], i.created_at, i.id))
    blocks: list[Block] = []
    taken: set[int] = set()
    for interest in ordered:
        mine = interest_pool(interest, pool)
        for key, title, sport, items in by_sport(interest, mine):
            stories = [a for a in fresh_stories(items, since, now, told) if a.id not in taken]
            taken |= {article.id for article in stories}
            context = context_sources(items, told)
            blocks.append(
                Block(key, title, interest.weight, sport, stories, context, interest=interest.topic)
            )
    return blocks


def by_sport(
    interest: Interest, items: list[Article]
) -> list[tuple[str, str, Sport | None, list[Article]]]:
    if interest.kind == "custom":
        return [(interest.topic, interest.topic, None, items)]
    name = CATALOG[interest.topic].name
    sports = TOPIC_FEEDS[interest.topic].sports
    if len(sports) == 1:
        return [(interest.topic, name, sports[0], items)]
    return [
        (
            f"{interest.topic}-{sport}",
            f"{name} · {sport}",
            sport,
            [a for a in items if source_sport(a.source, a.url) == sport],
        )
        for sport in sports
    ]


def sport_order(blocks: list[Block]) -> list[Block]:
    top: dict[Sport | None, int] = {}
    for block in blocks:
        top[block.sport] = max(top.get(block.sport, 0), WEIGHT_POINTS[block.weight])
    rank = {sport: number for number, sport in enumerate(SPORTS)}
    return sorted(blocks, key=lambda b: (-top[b.sport], rank.get(b.sport, len(SPORTS))))


def interest_pool(interest: Interest, pool: list[Article]) -> list[Article]:
    if interest.kind == "custom":
        return [a for a in pool if a.kind == "article" and mentions(a, interest.keywords)]
    feed = TOPIC_FEEDS[interest.topic]
    own = [article for article in pool if article.source in feed.sources]
    if feed.headline is None:
        return own
    league = {key for c in feed.competitions for key in TOPIC_FEEDS[c].sources}
    return own + [a for a in pool if a.source in league and belongs_to_team(a, feed)]


def belongs_to_team(article: Article, feed: TopicFeed) -> bool:
    kind = article.meta.get("type")
    if article.kind == "article":
        return feed.headline is not None and bool(feed.headline.search(article.title))
    if kind == "fixtures":
        games = article.meta.get("games", [])
        return any({game["home"], game["away"]} & feed.data_names for game in games)
    return bool(feed.data_names & set(article.meta.get("teams", [])))


def mentions(article: Article, keywords: list[str]) -> bool:
    for keyword in keywords:
        pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        if pattern.search(article.title) or len(pattern.findall(article.body)) >= 2:
            return True
    return False


def fresh_stories(
    pool: list[Article], since: datetime | None, now: datetime, told: set[int]
) -> list[Article]:
    news = [
        a
        for a in pool
        if a.kind == "article"
        and a.id not in told
        and now - NEWS_WINDOW <= a.published_at <= now
        and (since is None or a.fetched_at > since)
    ]
    results = [a for a in pool if a.meta.get("type") == "result" and a.id not in told]
    if since is None:
        results = latest_round(results)
    else:
        results = [a for a in results if a.fetched_at > since]
    return results + news


def context_sources(pool: list[Article], told: set[int]) -> list[Article]:
    standings = [a for a in pool if a.meta.get("type") == "standings" and a.id not in told]
    fixtures = [a for a in pool if a.meta.get("type") == "fixtures"]
    return latest_per_competition(standings) + latest_per_competition(fixtures)


def latest_round(results: list[Article]) -> list[Article]:
    last: dict[str, int] = {}
    for article in results:
        competition, number = article.meta["competition"], article.meta["round"]
        last[competition] = max(last.get(competition, number), number)
    return [a for a in results if a.meta["round"] == last[a.meta["competition"]]]


def latest_per_competition(articles: list[Article]) -> list[Article]:
    best: dict[str, Article] = {}
    for article in articles:
        key = (article.meta.get("round", 0), article.published_at)
        current = best.get(article.meta["competition"])
        if current is None or key > (current.meta.get("round", 0), current.published_at):
            best[article.meta["competition"]] = article
    return list(best.values())


def story_slots(length_minutes: int) -> int:
    target = round(length_minutes * 60 * CHARS_PER_SECOND)
    return (target - INTRO_CHARS - CLOSING_CHARS) // STORY_CHARS


def allocate(blocks: list[Block], slots: int) -> None:
    for block in blocks:
        if slots > 0 and block.stories:
            block.wanted, slots = 1, slots - 1

    def quotient(block: Block) -> float:
        used = sum(b.wanted for b in blocks if b.interest == block.interest)
        return WEIGHT_POINTS[block.weight] / (used + 1)

    while slots > 0:
        open_blocks = [b for b in blocks if b.stories and b.wanted < len(b.stories)]
        if not open_blocks:
            return
        best = max(open_blocks, key=lambda b: (quotient(b), -b.wanted))
        best.wanted, slots = best.wanted + 1, slots - 1


def pick_stories(run: Run, blocks: list[Block]) -> dict[str, list[tuple[list[Article], str]]]:
    ids: dict[str, Article] = {}
    allowed: dict[str, set[str]] = {}
    lines: list[str] = []
    for block in blocks:
        lines.append(f"\n## Block {block.key}: {block.title}. Pick up to {block.wanted} stories.")
        allowed[block.key] = set()
        for article in candidates(block):
            temp_id = f"C{len(ids) + 1}"
            ids[temp_id] = article
            allowed[block.key].add(temp_id)
            lines.append(describe(temp_id, article))
    result, call = run.llm.parse(
        model=run.config.openai_select_model,
        instructions=INSTRUCTIONS,
        prompt="\n".join(lines),
        schema=Picks,
        effort=SELECT_EFFORT,
    )
    run.calls.append(call)
    answered = {picked.key: picked for picked in result.blocks}
    used: set[str] = set()
    chosen: dict[str, list[tuple[list[Article], str]]] = {}
    for block in blocks:
        stories: list[tuple[list[Article], str]] = []
        picked = answered.get(block.key)
        for story in picked.stories if picked else []:
            valid = [t for t in story.source_ids if t in allowed[block.key] and t not in used]
            if valid and len(stories) < block.wanted:
                used |= set(valid)
                stories.append(([ids[temp] for temp in valid], story.reason))
        if not stories:
            stories = [([a], "Chosen by recency") for a in candidates(block)[: block.wanted]]
        chosen[block.key] = club_results(block, stories)
    return chosen


def club_results(
    block: Block, stories: list[tuple[list[Article], str]]
) -> list[tuple[list[Article], str]]:
    topic = CATALOG.get(block.interest)
    results = [a for a in block.stories if a.kind == "data" and a.meta.get("type") == "result"]
    if topic is None or topic.kind != "team" or not results or not stories:
        return stories
    latest = latest_per_competition(results)
    told = {article.id for articles, _ in stories for article in articles}
    missing = [article for article in latest if article.id not in told]
    if not missing:
        return stories
    host = next((n for n, (articles, _) in enumerate(stories) if set(articles) & set(results)), 0)
    articles, reason = stories[host]
    story_results = sorted(
        [a for a in articles if a in results] + missing, key=lambda a: a.published_at, reverse=True
    )
    others = [a for a in articles if a not in results]
    fixed = list(stories)
    fixed[host] = (story_results + others, reason)
    return fixed


def candidates(block: Block) -> list[Article]:
    ordered = sorted(block.stories, key=lambda a: (a.kind != "data", -a.published_at.timestamp()))
    return ordered[:MAX_CANDIDATES]


def describe(temp_id: str, article: Article) -> str:
    kind = (
        "official data" if article.kind == "data" else "official" if article.official else "outlet"
    )
    preview = " ".join(article.body[:PREVIEW_CHARS].split())
    return f"[{temp_id}] ({kind}, {article.published_at:%d %b}) {article.title} — {preview}"


def save_plan(
    run: Run,
    blocks: list[Block],
    picks: dict[str, list[tuple[list[Article], str]]],
    since: datetime | None,
    zone: ZoneInfo,
) -> dict:
    session, episode = run.session, run.episode
    session.execute(delete(EpisodeArticle).where(EpisodeArticle.episode_id == episode.id))
    source_ids: dict[int, str] = {}

    def source_id(article: Article, block: str, rank: int, reason: str | None) -> str:
        if article.id not in source_ids:
            source_ids[article.id] = f"S{len(source_ids) + 1}"
            session.add(
                EpisodeArticle(
                    episode_id=episode.id,
                    article_id=article.id,
                    source_id=source_ids[article.id],
                    block=block,
                    rank=rank,
                    reason=reason,
                )
            )
        return source_ids[article.id]

    plan_blocks = []
    for block in blocks:
        stories = [
            {
                "source_ids": [source_id(a, block.key, rank, reason) for a in articles],
                "reason": reason,
            }
            for rank, (articles, reason) in enumerate(picks[block.key], start=1)
        ]
        context = [source_id(a, block.key, 0, None) for a in block.context]
        plan_blocks.append(
            {
                "key": block.key,
                "title": block.title,
                "weight": block.weight,
                "sport": block.sport,
                "chars": len(stories) * STORY_CHARS,
                "stories": stories,
                "context_ids": context,
            }
        )
    today = run.now.astimezone(zone).date()
    coverage = (
        f"new since {spoken_date(since.astimezone(zone).date())}"
        if since
        else "catch-up: the listener's first episode"
    )
    plan = {
        "selected_at": run.now.isoformat(),
        "today": spoken_date(today),
        "coverage": coverage,
        "target_chars": round(run.podcast.length_minutes * 60 * CHARS_PER_SECOND),
        "intro_chars": INTRO_CHARS,
        "closing_chars": CLOSING_CHARS,
        "blocks": plan_blocks,
    }
    episode.plan = plan
    session.flush()
    return plan
