from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.demo import DEMO_USER_EMAIL
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


# The only place that changes when authentication is added.
def get_current_user(session: SessionDep) -> User:
    user = session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None:
        raise HTTPException(503, "The demo user does not exist yet: run python -m app.prestart")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
