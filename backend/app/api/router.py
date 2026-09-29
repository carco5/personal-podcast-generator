from fastapi import APIRouter

from app.api import catalog, episodes, generation, health, interests, internal, settings

api_router = APIRouter(prefix="/api/v1")
for module in (health, catalog, settings, interests, episodes, generation, internal):
    api_router.include_router(module.router)
