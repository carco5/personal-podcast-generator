from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PodcastSettings, User

DEMO_USER_EMAIL = "demo@example.com"

DEFAULT_SETTINGS = {
    "show_name": "Daily Briefing",
    "length_minutes": 5,
    "tone": "casual",
    "hosts": [
        {
            "role": "host",
            "name": "George",
            "personality": "Warm, energetic presenter who drives the episode and gives the facts.",
        },
        {
            "role": "analyst",
            "name": "Sarah",
            "personality": "Sharp, curious analyst who adds context, opinions and questions.",
        },
    ],
    "schedule_days": [1, 2, 3, 4, 5, 6, 7],
    "schedule_time": time(7, 0),
    "timezone": "Europe/Madrid",
}


def ensure_demo_user(session: Session) -> User:
    """Return the demo user, creating it with default settings if it does not exist."""
    user = session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None:
        user = User(email=DEMO_USER_EMAIL, name="Demo listener")
        session.add(user)
        session.flush()
        session.add(PodcastSettings(user_id=user.id, **DEFAULT_SETTINGS))
    return user
