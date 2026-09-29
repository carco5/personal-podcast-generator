from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.models import Interest, User
from app.pipeline.selection import running_order
from app.schemas import InterestCreate, InterestRead, InterestUpdate

router = APIRouter(prefix="/interests", tags=["interests"])

MAX_INTERESTS = 8

NOT_FOUND = {404: {"description": "The interest does not exist or belongs to another user"}}


def get_own_interest(session: SessionDep, user: User, interest_id: int) -> Interest:
    interest = session.scalar(
        select(Interest).where(Interest.id == interest_id, Interest.user_id == user.id)
    )
    if interest is None:
        raise HTTPException(404, "Interest not found")
    return interest


@router.get("")
def list_interests(session: SessionDep, user: CurrentUser) -> list[InterestRead]:
    return running_order(session.scalars(select(Interest).where(Interest.user_id == user.id)).all())


@router.post(
    "",
    status_code=201,
    responses={409: {"description": "The topic is already there, or there are already eight"}},
)
def create_interest(body: InterestCreate, session: SessionDep, user: CurrentUser) -> InterestRead:
    owned = session.scalars(select(Interest.topic).where(Interest.user_id == user.id)).all()
    if body.topic in owned:
        raise HTTPException(409, f"'{body.topic}' is already one of your interests")
    if len(owned) >= MAX_INTERESTS:
        raise HTTPException(409, f"You can have at most {MAX_INTERESTS} interests")
    interest = Interest(user_id=user.id, **body.model_dump())
    session.add(interest)
    session.commit()
    return interest


@router.patch("/{interest_id}", responses=NOT_FOUND)
def update_interest(
    interest_id: int, body: InterestUpdate, session: SessionDep, user: CurrentUser
) -> InterestRead:
    interest = get_own_interest(session, user, interest_id)
    interest.weight = body.weight
    session.commit()
    return interest


@router.delete("/{interest_id}", status_code=204, responses=NOT_FOUND)
def delete_interest(interest_id: int, session: SessionDep, user: CurrentUser) -> None:
    session.delete(get_own_interest(session, user, interest_id))
    session.commit()
