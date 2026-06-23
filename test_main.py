import pytest
from httpx import ASGITransport, AsyncClient

from database import fake_db
from main import app

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def clear_fake_db():
    fake_db.clear()
    yield
    fake_db.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def register_user(client: AsyncClient, username: str = "testuser", password: str = "testpass"):
    return await client.post(
        "/register",
        json={"username": username, "password": password},
    )


@pytest.mark.anyio
async def test_register():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await register_user(client)
        assert response.status_code == 200
        assert response.json()["msg"] == "注册成功"


@pytest.mark.anyio
async def test_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await register_user(client)
        response = await client.post(
            "/login",
            json={"username": "testuser", "password": "testpass"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_get_current_user_profile():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await register_user(client)
        login_resp = await client.post(
            "/login",
            json={"username": "testuser", "password": "testpass"},
        )
        token = login_resp.json()["access_token"]

        resp = await client.get(
            "/user/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert "created_at" in data


@pytest.mark.anyio
async def test_sms_send():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/sms/send", json={"phone": "13800000001"})
        assert resp.status_code == 200
        assert "验证码已发送" in resp.json()["msg"]


@pytest.mark.anyio
async def test_sms_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/sms/send", json={"phone": "13800000001"})
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        code = r.get("sms:code:13800000001")
        assert code is not None
        resp = await client.post("/sms/login", json={"phone": "13800000001", "code": code})
        assert resp.status_code == 200
        assert "access_token" in resp.json()


@pytest.mark.anyio
async def test_sms_freq_limit():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp1 = await client.post("/sms/send", json={"phone": "13800000009"})
        assert resp1.status_code == 200
        resp2 = await client.post("/sms/send", json={"phone": "13800000009"})
        assert resp2.status_code == 429
