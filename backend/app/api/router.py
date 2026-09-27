from fastapi import APIRouter

from app.api import catalog, episodes, health, interests, settings

api_router = APIRouter(prefix="/api/v1")
for module in (health, catalog, settings, interests, episodes):
    api_router.include_router(module.router)
