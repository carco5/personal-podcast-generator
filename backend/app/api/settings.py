from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.models import PodcastSettings
from app.schemas import PodcastSettingsRead, PodcastSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def read_settings(session: SessionDep, user: CurrentUser) -> PodcastSettingsRead:
    return session.get_one(PodcastSettings, user.id)


@router.put("")
def update_settings(
    body: PodcastSettingsUpdate, session: SessionDep, user: CurrentUser
) -> PodcastSettingsRead:
    settings = session.get_one(PodcastSettings, user.id)
    for field, value in body.model_dump().items():
        setattr(settings, field, value)
    session.commit()
    return settings
