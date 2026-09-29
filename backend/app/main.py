from pathlib import Path

from fastapi import FastAPI

from app.api.router import api_router
from app.config import ROOT

FRONTEND_DIST = ROOT / "frontend" / "dist"


def add_frontend(application: FastAPI, directory: Path) -> None:
    if directory.is_dir():
        application.frontend("/", directory=directory)


app = FastAPI(
    title="Personal Podcast Generator",
    version="0.1.0",
    description="Personal news podcasts on a schedule: interests, settings and episodes.",
)
app.include_router(api_router)
add_frontend(app, FRONTEND_DIST)
