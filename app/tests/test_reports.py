# app/tests/test_reports.py
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    await client.post("/api/v1/auth/register", json={
        "email": email, "full_name": "Report Tester",
        "password": "Str0ngP@ssw0rd!2026", "hourly_rate": 2000
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "Str0ngP@ssw0rd!2026"
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_earnings_summary(client: AsyncClient):
    headers = await get_auth_headers(client, "earnings@test.com")
    response = await client.get("/api/v1/reports/earnings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_projects" in data
    assert "total_earned" in data


async def test_invoice_pdf(client: AsyncClient):
    headers = await get_auth_headers(client, "invoice@test.com")

    # Create project
    proj = await client.post("/api/v1/projects/", json={
        "name": "Invoice Test Project",
        "client_name": "Test Client",
        "hourly_rate": 2000,
        "status": "active"
    }, headers=headers)
    assert proj.status_code == 201
    project_id = proj.json()["id"]

    # Log some hours
    log_hour = await client.post(f"/api/v1/projects/{project_id}/logs", json={
        "hours": 3,
        "description": "Backend development",
        "work_date": "2026-04-07"
    }, headers=headers)
    assert log_hour.status_code == 201

    # Download invoice
    response = await client.get(
        f"/api/v1/reports/invoice/{project_id}",
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    
    assert len(response.content) > 1000  # real PDF has substance

    # #downloade pdf 
    # with open("test_invoice.pdf", "wb") as f:
    #     f.write(response.content)


async def test_invoice_not_found(client: AsyncClient):
    headers = await get_auth_headers(client, "inv404@test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/v1/reports/invoice/{fake_id}",
        headers=headers
    )
    assert response.status_code == 404