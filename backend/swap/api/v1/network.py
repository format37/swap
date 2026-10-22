"""The signed-in user's network: who is how many handshakes away (ADR-0028).

The wizard draws it as rings around its author, and counts who an order's reach will
reach. It names people beyond one's own links, which the owner's picture needs
(QUESTIONS J2); beyond three handshakes it only counts them.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from swap.api.deps import CurrentUser, Db
from swap.api.errors import Problem
from swap.api.v1.people import Person
from swap.models import User
from swap.network import FAR, Graph
from swap.users import full_name

router = APIRouter(tags=["network"], responses={401: {"model": Problem}})


class Ring(BaseModel):
    # Handshakes away: 1, 2 or 3.
    distance: int
    people: list[Person]


class Network(BaseModel):
    # The first three rings, nearest first; an empty ring is still listed.
    rings: list[Ring]
    # How many are four handshakes or more away: counted, not named.
    farther: int


@router.get("/network")
async def get_network(user: CurrentUser, db: Db) -> Network:
    away = (await Graph.load(db)).rings(user.id)
    near = [person for person, distance in away.items() if distance < FAR]
    people = sorted(
        await db.scalars(select(User).where(User.id.in_(near))), key=lambda u: full_name(u).lower()
    )
    return Network(
        rings=[
            Ring(
                distance=distance,
                people=[Person.of(person) for person in people if away[person.id] == distance],
            )
            for distance in range(1, FAR)
        ],
        farther=sum(1 for distance in away.values() if distance == FAR),
    )
