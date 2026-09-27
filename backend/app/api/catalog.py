from fastapi import APIRouter

from app.catalog import CATALOG, Topic

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("")
def list_topics() -> list[Topic]:
    return list(CATALOG.values())
