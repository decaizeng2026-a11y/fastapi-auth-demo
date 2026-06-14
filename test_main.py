import pytest
from httpx import ASGITransport, AsyncClient
from main import app


pytestmark = pytest.mark.anyio


@pytest.mark.anyio
async def test_register():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/register", json={"username": "testuser", "password": "testpass"})
        assert response.status_code == 200
        assert "msg" in response.json()


@pytest.mark.anyio
async def test_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/login", json={"username": "testuser", "password": "testpass"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


@pytest.mark.anyio
async def test_protected_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 先登录拿 Token
        login_resp = await client.post("/login", json={"username": "testuser", "password": "testpass"})
        token = login_resp.json()["access_token"]

        # 带 Token 访问受保护接口
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/user/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert "created_at" in data