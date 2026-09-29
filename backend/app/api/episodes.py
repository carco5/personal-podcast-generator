from datetime import UTC, datetime
from math import ceil
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.catalog import CATALOG
from app.config import Settings
from app.models import Article, Episode, EpisodeArticle, Interest, ListenEvent, StageRun, User
from app.pipeline.checks import TAG
from app.schemas import (
    Chapter,
    CitedSource,
    EpisodeDetail,
    EpisodePage,
    EpisodeRead,
    ListenEventCreate,
    Section,
    Turn,
)
from app.sources.registry import SOURCE_NAMES

router = APIRouter(prefix="/episodes", tags=["episodes"])


def get_own_episode(session: Session, user: User, episode_id: int) -> Episode:
    episode = session.scalar(
        select(Episode).where(Episode.id == episode_id, Episode.user_id == user.id)
    )
    if episode is None:
        raise HTTPException(404, "Episode not found")
    return episode


def require_generation_keys(settings: Settings) -> None:
    missing = settings.missing_generation_keys()
    if missing:
        raise HTTPException(503, f"Episode generation needs {' and '.join(missing)} in .env")


IN_FLIGHT_INDEX = "uq_episodes_one_in_flight_per_user"

NOT_FOUND = {404: {"description": "The episode does not exist or belongs to another user"}}
KEYS_MISSING = {
    503: {
        "description": "OPENAI_API_KEY is missing, or ELEVENLABS_API_KEY when WORKER_VOICE is "
        "elevenlabs"
    }
}


def commit_or_conflict(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if error.orig.diag.constraint_name != IN_FLIGHT_INDEX:
            raise
        raise HTTPException(409, "An episode is already being generated") from None


def running_stages(session: Session, episodes: list[Episode]) -> dict[int, str]:
    ids = [episode.id for episode in episodes if episode.status == "in_progress"]
    if not ids:
        return {}
    rows = session.execute(
        select(StageRun.episode_id, StageRun.stage).where(
            StageRun.episode_id.in_(ids), StageRun.status == "in_progress"
        )
    ).all()
    return {episode_id: stage for episode_id, stage in rows}


def summary(episode: Episode, stages: dict[int, str]) -> EpisodeRead:
    selected_at = (episode.plan or {}).get("selected_at")
    news_as_of = datetime.fromisoformat(selected_at) if selected_at else None
    return EpisodeRead.model_validate(episode).model_copy(
        update={"stage": stages.get(episode.id), "news_as_of": news_as_of}
    )


SECTION_TITLES = {"intro": "Intro", "closing": "Closing"}


def section_title(key: str) -> str:
    if key in SECTION_TITLES:
        return SECTION_TITLES[key]
    return CATALOG[key].name if key in CATALOG else key


def readable(text: str) -> str:
    return " ".join(TAG.sub("", text).split())


def episode_detail(session: Session, episode: Episode) -> EpisodeDetail:
    transcript = [
        Section(
            key=segment["key"],
            title=section_title(segment["key"]),
            turns=[
                Turn(speaker=t["speaker"], text=readable(t["text"]), source_ids=t["source_ids"])
                for t in segment["turns"]
            ],
        )
        for segment in (episode.script or {}).get("segments", [])
    ]
    cited = {sid for section in transcript for turn in section.turns for sid in turn.source_ids}
    rows = session.execute(
        select(EpisodeArticle, Article)
        .join(Article, Article.id == EpisodeArticle.article_id)
        .where(EpisodeArticle.episode_id == episode.id)
    ).all()
    sources = [
        CitedSource(
            source_id=link.source_id,
            section=link.block,
            outlet=SOURCE_NAMES.get(article.source, article.source),
            official=article.official,
            kind=article.kind,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
        )
        for link, article in rows
        if link.source_id in cited
    ]
    sources.sort(key=lambda source: int(source.source_id[1:]))
    chapters = [
        Chapter(key=c["key"], title=section_title(c["key"]), start_seconds=c["start"])
        for c in episode.chapters or []
    ]
    return EpisodeDetail(
        **summary(episode, running_stages(session, [episode])).model_dump(),
        chapters=chapters,
        transcript=transcript,
        sources=sources,
    )


@router.get("")
def list_episodes(
    session: SessionDep,
    user: CurrentUser,
    page: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> EpisodePage:
    mine = Episode.user_id == user.id
    total = session.scalar(select(func.count()).select_from(Episode).where(mine))
    rows = session.scalars(
        select(Episode)
        .where(mine)
        .order_by(Episode.scheduled_for.desc(), Episode.id.desc())
        .offset(page * limit)
        .limit(limit)
    ).all()
    page_count = ceil(total / limit)
    stages = running_stages(session, list(rows))
    return EpisodePage(
        episodes=[summary(row, stages) for row in rows],
        page_count=page_count,
        next_page=page + 1 if page + 1 < page_count else None,
    )


@router.get("/{episode_id}", responses=NOT_FOUND)
def read_episode(episode_id: int, session: SessionDep, user: CurrentUser) -> EpisodeDetail:
    return episode_detail(session, get_own_episode(session, user, episode_id))


@router.get(
    "/{episode_id}/audio",
    response_class=FileResponse,
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "The episode as MP3"},
        **NOT_FOUND,
    },
)
def episode_audio(
    episode_id: int, session: SessionDep, user: CurrentUser, settings: SettingsDep
) -> FileResponse:
    episode = get_own_episode(session, user, episode_id)
    if episode.audio_path is None:
        raise HTTPException(404, "This episode has no audio yet")
    path = settings.data_dir / episode.audio_path
    if not path.is_file():
        raise HTTPException(404, "The audio file is missing")
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename=f"episode-{episode.id}.mp3",
        content_disposition_type="inline",
    )


@router.post(
    "/{episode_id}/listen-events",
    status_code=204,
    responses={**NOT_FOUND, 409: {"description": "The episode has no audio to listen to"}},
)
def record_listen_event(
    episode_id: int, body: ListenEventCreate, session: SessionDep, user: CurrentUser
) -> None:
    episode = get_own_episode(session, user, episode_id)
    if episode.status != "completed":
        raise HTTPException(409, "Only completed episodes can be listened to")
    session.add(
        ListenEvent(episode_id=episode.id, kind=body.kind, position_seconds=body.position_seconds)
    )
    session.commit()


@router.post(
    "",
    status_code=202,
    responses={
        **KEYS_MISSING,
        409: {"description": "No interests yet, or an episode is already being generated"},
    },
)
def generate_episode(session: SessionDep, user: CurrentUser, settings: SettingsDep) -> EpisodeRead:
    require_generation_keys(settings)
    if session.scalar(select(Interest.id).where(Interest.user_id == user.id).limit(1)) is None:
        raise HTTPException(409, "Add at least one interest before generating an episode")
    episode = Episode(user_id=user.id, trigger="manual", scheduled_for=datetime.now(UTC))
    session.add(episode)
    commit_or_conflict(session)
    return episode


@router.post(
    "/{episode_id}/retry",
    status_code=202,
    responses={
        **NOT_FOUND,
        **KEYS_MISSING,
        409: {"description": "The episode did not fail, or another one is being generated"},
    },
)
def retry_episode(
    episode_id: int, session: SessionDep, user: CurrentUser, settings: SettingsDep
) -> EpisodeRead:
    require_generation_keys(settings)
    return requeue(session, get_own_episode(session, user, episode_id))


def requeue(session: Session, episode: Episode) -> Episode:
    if episode.status != "failed":
        raise HTTPException(409, "Only failed episodes can be retried")
    episode.status = "queued"
    episode.status_reason = None
    episode.started_at = None
    episode.finished_at = None
    commit_or_conflict(session)
    return episode
