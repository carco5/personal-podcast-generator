import argparse
import logging
from collections.abc import Iterable
from datetime import timedelta

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import engine
from app.models import Article, EpisodeArticle
from app.sources.base import Source, SourceItem
from app.sources.http import Fetcher
from app.sources.registry import catalogue_sources

log = logging.getLogger(__name__)

RETENTION = timedelta(days=30)
MAX_ERROR_CHARS = 300


def short_error(error: Exception) -> str:
    first_line = (str(error).splitlines() or [""])[0]
    return f"{type(error).__name__}: {first_line}"[:MAX_ERROR_CHARS]


def ingest(
    session: Session, sources: Iterable[Source], fetcher: Fetcher, *, refresh: bool = False
) -> dict[str, dict]:
    report: dict[str, dict] = {}
    for source in sources:
        stored = select(Article.url).where(Article.source == source.key)
        known = set() if refresh else set(session.scalars(stored))
        try:
            items = list(source.items(fetcher, known))
            saved = save(session, source, items)
            session.commit()
        except Exception as error:
            session.rollback()
            log.exception("Source %s failed", source.key)
            report[source.key] = {"error": short_error(error)}
            continue
        report[source.key] = {"items": len(items), "saved": saved}
    purged = purge(session)
    session.commit()
    report["purged"] = {"articles": purged}
    return report


def save(session: Session, source: Source, items: list[SourceItem]) -> int:
    unique = {item.url: item for item in items}
    if not unique:
        return 0
    rows = [
        {
            **item.model_dump(),
            "source": source.key,
            "language": source.language,
            "official": source.official,
        }
        for item in unique.values()
    ]
    statement = insert(Article).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[Article.url],
        set_={
            "title": statement.excluded.title,
            "body": statement.excluded.body,
            "published_at": statement.excluded.published_at,
            "meta": statement.excluded.meta,
            "fetched_at": func.now(),
        },
        where=(Article.kind == "data")
        & (
            Article.body.is_distinct_from(statement.excluded.body)
            | Article.meta.is_distinct_from(statement.excluded.meta)
        ),
    )
    return len(session.scalars(statement.returning(Article.id)).all())


def purge(session: Session) -> int:
    in_use = exists().where(EpisodeArticle.article_id == Article.id)
    statement = delete(Article).where(Article.fetched_at < func.now() - RETENTION, ~in_use)
    return session.execute(statement).rowcount


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the catalogue sources (free GETs).")
    parser.add_argument("--source", action="append", help="only this source key (repeatable)")
    parser.add_argument("--refresh", action="store_true", help="re-read items already stored")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    with Session(engine) as session:
        catalogue = catalogue_sources(get_settings())
        sources = [catalogue[key] for key in args.source] if args.source else catalogue.values()
        report = ingest(session, sources, Fetcher(), refresh=args.refresh)
    for key, result in report.items():
        print(f"{key:>26}: {result}")


if __name__ == "__main__":
    main()
