from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(
    title="Personal Podcast Generator",
    version="0.1.0",
    description="Personal news podcasts on a schedule: interests, settings and episodes.",
)
app.include_router(api_router)
