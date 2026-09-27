from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.deps import SessionDep
from app.schemas import Health

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", responses={503: {"description": "The database is unavailable"}})
def health(session: SessionDep) -> Health:
    try:
        session.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(503, "Database unavailable") from None
    return Health(status="ok")
