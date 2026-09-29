from datetime import UTC, datetime
from math import ceil
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.config import Settings
from app.models import Episode, Interest, User
from app.schemas import EpisodePage, EpisodeRead

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
    return EpisodePage(
        episodes=[EpisodeRead.model_validate(row) for row in rows],
        page_count=page_count,
        next_page=page + 1 if page + 1 < page_count else None,
    )


@router.get("/{episode_id}", responses=NOT_FOUND)
def read_episode(episode_id: int, session: SessionDep, user: CurrentUser) -> EpisodeRead:
    return get_own_episode(session, user, episode_id)


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
    episode = get_own_episode(session, user, episode_id)
    if episode.status != "failed":
        raise HTTPException(409, "Only failed episodes can be retried")
    episode.status = "queued"
    episode.status_reason = None
    episode.started_at = None
    episode.finished_at = None
    commit_or_conflict(session)
    return episode
