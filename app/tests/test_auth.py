# tests/test_auth.py
from httpx import AsyncClient


async def test_register_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "rajan@test.com",
        "full_name": "Rajan Test",
        "password": "Str0ngP@ssw0rd!2026",
        "hourly_rate": 1500
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "rajan@test.com"
    assert "hashed_password" not in data  # never leak this


async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@test.com",
        "full_name": "Someone",
        "password": "Str0ngP@ssw0rd!2026",
        "hourly_rate": 1000
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400


async def test_login_success(client: AsyncClient):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "full_name": "Login User",
        "password": "Str0ngP@ssw0rd!2026",
        "hourly_rate": 1000
    })
    # Now login
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "Str0ngP@ssw0rd!2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpass@test.com",
        "full_name": "User",
        "password": "Str0ngP@ssw0rd!2026",
        "hourly_rate": 1000
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "wrongpass@test.com",
        "password": "WrongP@ssw0rd!2026"
    })
    assert response.status_code == 401


async def test_login_non_existent_user(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={
        "email": "notfound@test.com",
        "password": "Str0ngP@ssw0rd!2026"
    })
    assert response.status_code == 401

async def test_protected_route_without_token(client: AsyncClient):
    response = await client.get("/api/v1/projects/")
    assert response.status_code == 401

