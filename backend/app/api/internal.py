from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep, SettingsDep
from app.api.episodes import KEYS_MISSING, requeue, require_generation_keys
from app.metrics import operations_metrics, product_metrics
from app.models import Episode, User
from app.schemas import EpisodeRead, OperationsMetrics, ProductMetrics

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/product")
def read_product(session: SessionDep, include_simulated: bool = True) -> ProductMetrics:
    return product_metrics(session, datetime.now(UTC), include_simulated)


@router.get("/operations")
def read_operations(
    session: SessionDep, settings: SettingsDep, include_simulated: bool = True
) -> OperationsMetrics:
    return operations_metrics(session, datetime.now(UTC), include_simulated, settings)


@router.post(
    "/episodes/{episode_id}/retry",
    status_code=202,
    responses={
        404: {"description": "The episode does not exist"},
        **KEYS_MISSING,
        409: {
            "description": "The episode is simulated or did not fail, "
            "or another one is being generated"
        },
    },
)
def retry_run(episode_id: int, session: SessionDep, settings: SettingsDep) -> EpisodeRead:
    require_generation_keys(settings)
    episode = session.get(Episode, episode_id)
    if episode is None:
        raise HTTPException(404, "Episode not found")
    if session.get_one(User, episode.user_id).is_synthetic:
        raise HTTPException(409, "Simulated episodes cannot be generated")
    return requeue(session, episode)
