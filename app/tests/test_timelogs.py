# app/tests/test_timelogs.py
from logging import warning

from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Test User",
        "password": "Str0ngP@ssw0rd!2026",
        "hourly_rate": 2000
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "Str0ngP@ssw0rd!2026"
    })
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def create_project(client: AsyncClient, headers: dict, name: str = "Test Project") -> str:
    response = await client.post("/api/v1/projects/", json={
        "name": name,
        "description": "A test project",
        "client_name": "Test Client",
        "hourly_rate": 1500,
        "budget": 10000
    }, headers=headers)
    return response.json()["id"]


async def test_log_hours(client: AsyncClient):
    headers = await get_auth_headers(client, "timelog1@test.com")
    project_id = await create_project(client, headers)

    response = await client.post(f"/api/v1/projects/{project_id}/logs", json={
        "hours": 3.5,
        "description": "Worked on feature X",
        "work_date": "2026-04-07"
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["hours"] == 3.5
    assert data["project_id"] == project_id


async def test_list_time_logs(client: AsyncClient):
    headers = await get_auth_headers(client, "timelog2@test.com")
    project_id = await create_project(client, headers)

    # Log twice
    for hours in [2.0, 4.5]:
        await client.post(f"/api/v1/projects/{project_id}/logs", json={
            "hours": hours,
            "description": "Work session",
            "work_date": "2026-04-07"
        }, headers=headers)

    response = await client.get(f"/api/v1/projects/{project_id}/logs", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_cannot_log_on_other_users_project(client: AsyncClient):
    headers_a = await get_auth_headers(client, "tl_usera@test.com")
    headers_b = await get_auth_headers(client, "tl_userb@test.com")
    project_id = await create_project(client, headers_a)

    response = await client.post(f"/api/v1/projects/{project_id}/logs", json={
        "hours": 1.0,
        "description": "Sneaky work",
        "work_date": "2026-04-07"
    }, headers=headers_b)
    assert response.status_code == 404