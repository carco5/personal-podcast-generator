from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.models import Interest, PodcastSettings
from app.schedule import next_slot
from app.schemas import Generation

router = APIRouter(prefix="/generation", tags=["generation"])


@router.get("")
def read_generation(session: SessionDep, user: CurrentUser, settings: SettingsDep) -> Generation:
    podcast = session.get_one(PodcastSettings, user.id)
    has_interests = session.scalar(select(Interest.id).where(Interest.user_id == user.id).limit(1))
    return Generation(
        missing_keys=settings.missing_generation_keys(),
        voice=settings.worker_voice,
        next_episode_at=next_slot(podcast, datetime.now(UTC)) if has_interests else None,
    )
