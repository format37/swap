"""The score (QUESTIONS J5, ADR-0029): how many different people someone has a settled deal
with. Repeat deals add nothing, and only settled ones count."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.test_deals import World
from tests.test_links import GIO, Headers, linked

Sessions = async_sessionmaker[AsyncSession]


async def settle(world: World, proposer: Headers, amount: str = "10000.00") -> dict[str, Any]:
    """A deal on Alex's order, proposed by `proposer`, accepted and received both ways."""
    deal = await world.propose(proposer, amount=amount)
    await world.ok(world.alex, deal, "accept")
    await world.ok(world.alex, deal, "legs/1/received")
    settled: dict[str, Any] = await world.ok(proposer, deal, "legs/2/received")
    assert settled["status"] == "settled"
    return settled


async def score(client: AsyncClient, headers: Headers) -> int:
    me: dict[str, Any] = (await client.get("/api/v1/me", headers=headers)).json()
    return int(me["score"])


async def test_a_new_person_scores_nothing(client: AsyncClient, sessionmaker: Sessions) -> None:
    world = await World(client, sessionmaker).build()
    assert await score(client, world.alex) == 0
    links = (await client.get("/api/v1/links", headers=world.alex)).json()
    assert [link["person"]["score"] for link in links["active"]] == [0]


async def test_unsettled_deals_count_for_nothing(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    world = await World(client, sessionmaker).build()
    declined = await world.propose()
    await world.ok(world.alex, declined, "decline")
    cancelled = await world.propose()
    await world.ok(world.alex, cancelled, "accept")
    await world.ok(world.nino, cancelled, "cancel")
    running = await world.propose()
    await world.ok(world.alex, running, "accept")
    assert await score(client, world.alex) == 0
    assert await score(client, world.nino) == 0


async def test_one_point_per_person_however_many_deals(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    world = await World(client, sessionmaker).build()
    await settle(world, world.nino)
    # Settling again with the same person adds nothing: no pumping each other's score.
    await settle(world, world.nino)
    assert await score(client, world.alex) == 1
    assert await score(client, world.nino) == 1
    # Someone new adds a point, to both of them.
    await linked(client, sessionmaker, world.alex, GIO)
    await settle(world, world.gio)
    assert await score(client, world.alex) == 2
    assert await score(client, world.gio) == 1


async def test_the_score_goes_wherever_a_person_is_shown(
    client: AsyncClient, sessionmaker: Sessions
) -> None:
    world = await World(client, sessionmaker).build()
    deal = await settle(world, world.nino)
    assert deal["proposer"]["score"] == deal["acceptor"]["score"] == 1
    card = (await client.get(f"/api/v1/orders/{world.order['id']}", headers=world.nino)).json()
    assert card["author"]["score"] == 1
    network = (await client.get("/api/v1/network", headers=world.nino)).json()
    assert [person["score"] for person in network["rings"][0]["people"]] == [1]
