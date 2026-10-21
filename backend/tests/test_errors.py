from httpx import AsyncClient


async def test_an_unknown_path_is_a_404_problem(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nothing-here")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "code": "not_found",
    }


async def test_a_wrong_method_is_a_405_problem_with_allow(client: AsyncClient) -> None:
    response = await client.post("/healthz")
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
    assert "GET" in response.headers["allow"]
