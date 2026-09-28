from app.catalog import CATALOG
from app.pipeline.common import Run, StageFailed
from app.sources.base import Source
from app.sources.guardian import GuardianSearchSource
from app.sources.ingest import ingest
from app.sources.registry import TOPIC_FEEDS, catalogue_sources


def episode_sources(run: Run) -> dict[str, Source]:
    available = catalogue_sources(run.config)
    wanted: set[str] = set()
    keywords: list[str] = []
    for interest in run.interests:
        if interest.kind == "custom":
            wanted |= set(available)
            keywords += interest.keywords
            continue
        feed = TOPIC_FEEDS[interest.topic]
        wanted |= set(feed.sources)
        for competition in feed.competitions:
            wanted |= set(TOPIC_FEEDS[competition].sources)
    sources = {key: available[key] for key in sorted(wanted) if key in available}
    if keywords and run.config.guardian_api_key is not None:
        query = " OR ".join(f'"{keyword}"' for keyword in keywords)
        sources["guardian-search"] = GuardianSearchSource(query, run.config.guardian_api_key)
    return sources


def fetch(run: Run) -> dict:
    sources = episode_sources(run)
    report = ingest(run.session, sources.values(), run.fetcher)
    failed = [key for key in sources if "error" in report.get(key, {})]
    if sources and len(failed) == len(sources):
        raise StageFailed(f"fetch: every source failed ({', '.join(failed)})")
    topics = [CATALOG[i.topic].name if i.kind == "catalog" else i.topic for i in run.interests]
    return {"topics": topics, "sources": report}
