import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from auth import router
from database import get_async_session, User
from auth import UserCreate

# Inicjalizacja minimalnej aplikacji do testów
app = FastAPI()
app.include_router(router)

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session

@pytest.fixture
def client(mock_session):
    """Zastępuje zależność bazy danych i dostarcza klienta HTTP."""
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")

@pytest.fixture
def mock_user():
    """Przykładowy obiekt użytkownika."""
    user = User(
        id=1,
        username="testuser",
        hashed_password="hashed_password",
        role="user",
        totp_enabled=False,
        totp_secret=None
    )
    return user


@pytest.mark.asyncio
async def test_register_user_success(client, mock_session):
    mock_session.commit = AsyncMock()
    
    async def mock_refresh(obj):
        obj.id = 1
        
    mock_session.refresh.side_effect = mock_refresh

    with patch("auth.router_user.get_password_hash", return_value="hashed_password"):
        response = await client.post(
            "/auth/register",
            json={"username": "nowy_user", "password": "secure_password", "email": "test@test.com"}
        )

    assert response.status_code == 200
    assert response.json()["id"] == 1


@pytest.mark.asyncio
async def test_register_user_duplicate(client, mock_session):
    mock_session.commit.side_effect = IntegrityError(None, None, Exception("Duplicate"))
    mock_session.rollback = AsyncMock()

    response = await client.post(
        "/auth/register",
        json={"username": "istniejacy_user", "password": "secure_password", "email": "test@test.com"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Użytkownik o takim loginie lub emailu już istnieje."
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, mock_session):
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    response = await client.post(
        "/auth/login",
        json={"username": "wronguser", "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Niepoprawny login lub hasło"


@pytest.mark.asyncio
async def test_login_success_no_2fa(client, mock_session, mock_user):
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("auth.router_user.verify_password", return_value=True), \
         patch("auth.router_user.create_access_token", return_value="fake_access"), \
         patch("auth.router_user.create_refresh_token", return_value="fake_refresh"):
        
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "correctpassword"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_2fa_required(client, mock_session, mock_user):
    mock_user.totp_enabled = True
    
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("auth.router_user.verify_password", return_value=True), \
         patch("auth.router_user.create_preauth_token", return_value="fake_preauth"):
        
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "correctpassword"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout(client, mock_session):
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    client.cookies.set("refresh_token", "valid_refresh_token", domain="test")

    response = await client.post("/auth/logout")

    assert response.status_code == 200