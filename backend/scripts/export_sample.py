"""Export the sample episode to app/sample_episode.json, so a fresh database starts with it.

Run from backend/:
    python scripts/export_sample.py 23
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.demo import SAMPLE_EPISODE
from app.models import Article, Episode, EpisodeArticle


def article_data(article: Article) -> dict:
    return {
        "source": article.source,
        "kind": article.kind,
        "official": article.official,
        "language": article.language,
        "url": article.url,
        "title": article.title,
        "body": article.body if article.kind == "data" else "",
        "published_at": article.published_at.isoformat(),
        "meta": article.meta,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_id", type=int)
    episode_id = parser.parse_args().episode_id
    with Session(engine) as session:
        episode = session.get_one(Episode, episode_id)
        rows = session.execute(
            select(EpisodeArticle, Article)
            .join(Article, Article.id == EpisodeArticle.article_id)
            .where(EpisodeArticle.episode_id == episode_id)
        ).all()
        sources = [
            {
                "source_id": link.source_id,
                "block": link.block,
                "rank": link.rank,
                "reason": link.reason,
                "article": article_data(article),
            }
            for link, article in sorted(rows, key=lambda row: int(row[0].source_id[1:]))
        ]
        data = {
            "episode": {
                "title": episode.title,
                "trigger": episode.trigger,
                "scheduled_for": episode.scheduled_for.isoformat(),
                "created_at": episode.created_at.isoformat(),
                "started_at": episode.started_at.isoformat(),
                "finished_at": episode.finished_at.isoformat(),
                "attempts": episode.attempts,
                "duration_seconds": episode.duration_seconds,
                "chapters": episode.chapters,
                "script": episode.script,
                "plan": episode.plan,
            },
            "sources": sources,
        }
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    Path(SAMPLE_EPISODE).write_text(text, encoding="utf-8")
    print(f"Wrote {SAMPLE_EPISODE} ({len(sources)} sources, {len(text) // 1024} KiB)")


if __name__ == "__main__":
    main()
