# tests/test_projects.py
import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# HELPER — we need a logged-in user for every project test
# ---------------------------------------------------------------------------

async def get_auth_headers(client: AsyncClient, email: str = "proj@test.com") -> dict:
    """Register + login, return Authorization header."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Project Tester",
        "password": "Str0ngP@ssw0rd!2026",
        "hourly_rate": 2000
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Str0ngP@ssw0rd!2026"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_project(client: AsyncClient):
    headers = await get_auth_headers(client, "create@test.com")
    response = await client.post("/api/v1/projects/", json={
        "name": "Test Project",
        "description": "A test project",
        "client_name": "Test Client",
        "hourly_rate": 1500,
        "budget": 10000
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data


async def test_list_projects(client: AsyncClient):
    headers = await get_auth_headers(client, "list@test.com")
    # Create two projects
    for name in ["Project A", "Project B"]:
        await client.post("/api/v1/projects/", json={
            "name": name,
            "description": f"{name} description",
            "client_name": f"{name} Client",
            "hourly_rate": 1000,
            "budget": 5000
        }, headers=headers)

    response = await client.get("/api/v1/projects/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2


async def test_get_project_not_found(client: AsyncClient):
    headers = await get_auth_headers(client, "notfound@test.com")
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/projects/{fake_id}", headers=headers)
    assert response.status_code == 404


async def test_cannot_access_other_users_project(client: AsyncClient):
    """Object-level auth — user A cannot see user B's project."""
    headers_a = await get_auth_headers(client, "usera@test.com")
    headers_b = await get_auth_headers(client, "userb@test.com")

    # User A creates a project
    create_resp = await client.post("/api/v1/projects/", json={
        "name": "User A's Project",
        "description": "Owned by User A",
        "client_name": "Client A",
        "hourly_rate": 1200,
        "budget": 8000
    }, headers=headers_a)
    project_id = create_resp.json()["id"]

    # User B tries to access it
    response = await client.get(f"/api/v1/projects/{project_id}", headers=headers_b)
    assert response.status_code == 404  # not 403 — we don't confirm it exists


async def test_update_project(client: AsyncClient):
    headers = await get_auth_headers(client, "update@test.com")
    create_resp = await client.post("/api/v1/projects/", json={
        "name": "Old Name",
        "description": "Old description",
        "client_name": "Old Client",
        "hourly_rate": 1000,
        "budget": 5000
    }, headers=headers)
    project_id = create_resp.json()["id"]

    response = await client.patch(f"/api/v1/projects/{project_id}", json={
        "name": "New Name",
        "status": "completed"
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["status"] == "completed"


async def test_delete_project(client: AsyncClient):
    headers = await get_auth_headers(client, "delete@test.com")
    create_resp = await client.post("/api/v1/projects/", json={
        "name": "To Be Deleted",
        "description": "This project will be deleted",
        "client_name": "Delete Client",
        "hourly_rate": 1100,
        "budget": 6000
    }, headers=headers)
    project_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert response.status_code == 204

    # Confirm it's gone (soft deleted)
    get_resp = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 404