import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError

# Zastąp 'auth.router_user' właściwą ścieżką do pliku routera
from auth.router_user import router
from auth.limiter import limiter
from auth.dependencies_user import get_current_user
from database import get_async_session, User, BlacklistedToken

# Konfiguracja środowiska testowego FastAPI
app = FastAPI()
app.state.limiter = limiter  # Wymagane przez slowapi
app.include_router(router)

# Klasa pomocnicza do symulowania wyników z SQLAlchemy (session.execute)
class MockResult:
    def __init__(self, data):
        self.data = data
    def scalars(self):
        return self
    def first(self):
        if isinstance(self.data, list):
            return self.data[0] if self.data else None
        return self.data
    def scalar_one_or_none(self):
        return self.first()

@pytest.fixture
def mock_session():
    """Mock asynchronicznej sesji bazy danych."""
    session = AsyncMock()
    # W SQLAlchemy session.add() jest metodą synchroniczną. 
    # Wymuszamy, by mock traktował ją jako zwykłą funkcję, a nie korutynę.
    session.add = MagicMock() 
    return session

@pytest.fixture
def mock_user():
    """Mock standardowego użytkownika."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "test_user"
    user.role = "user"
    user.hashed_password = "hashed_secret"
    user.totp_enabled = False
    user.totp_secret = None
    return user

@pytest.fixture(autouse=True)
def setup_overrides(mock_session, mock_user):
    """Zastępuje zależności FastAPI (wstrzykiwanie sesji i użytkownika)."""
    app.dependency_overrides[get_async_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides = {}

client = TestClient(app)


# --- TESTY: /login ---

@patch("auth.router_user.verify_password")
def test_login_success_no_2fa(mock_verify_pwd, mock_session, mock_user):
    """Weryfikuje: Poprawne logowanie gdy 2FA jest wyłączone."""
    mock_session.execute.return_value = MockResult(mock_user)
    mock_verify_pwd.return_value = True

    response = client.post("/auth/login", json={"username": "test_user", "password": "password123"})
    
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.cookies.get("refresh_token") is not None

@patch("auth.router_user.verify_password")
def test_login_wrong_credentials(mock_verify_pwd, mock_session):
    """Weryfikuje: Zwracanie błędu 401 przy złym haśle."""
    mock_session.execute.return_value = MockResult(None) # Brak usera
    
    response = client.post("/auth/login", json={"username": "wrong", "password": "123"})
    assert response.status_code == 401
    assert "Niepoprawny login lub hasło" in response.json()["detail"]

@patch("auth.router_user.create_preauth_token")
@patch("auth.router_user.verify_password")
def test_login_requires_2fa(mock_verify_pwd, mock_create_preauth, mock_session, mock_user):
    """Weryfikuje: Przekierowanie do kroku 2FA, gdy użytkownik ma włączone TOTP."""
    mock_user.totp_enabled = True
    mock_session.execute.return_value = MockResult(mock_user)
    mock_verify_pwd.return_value = True
    mock_create_preauth.return_value = "dummy_preauth_token"

    response = client.post("/auth/login", json={"username": "test_user", "password": "password123"})
    
    assert response.status_code == 200
    assert response.json()["step"] == "2fa_required"
    assert response.json()["preauth_token"] == "dummy_preauth_token"


# --- TESTY: /logout ---

def test_logout_success(mock_session):
    """Weryfikuje: Poprawne wylogowanie z unieważnieniem refresh tokena."""
    mock_session.execute.return_value = MockResult(None) # Token nie jest na czarnej liście
    client.cookies.set("refresh_token", "dummy_token")
    
    response = client.post("/auth/logout")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Wylogowano pomyślnie."
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


# --- TESTY: /register ---

def test_register_success(mock_session):
    """Weryfikuje: Pomyślną rejestrację konta użytkownika."""
    
    # Kiedy kod wywoła "await session.refresh(new_user)", 
    # nasza funkcja poboczna (side_effect) nada mu sztuczne ID, symulując zachowanie bazy SQL.
    async def mock_refresh(obj):
        obj.id = 1
        
    mock_session.refresh.side_effect = mock_refresh

    response = client.post("/auth/register", json={"username": "new_user", "password": "password123"})
    
    assert response.status_code == 200
    assert response.json()["username"] == "new_user"
    assert response.json()["id"] == 1
    mock_session.commit.assert_called_once()

def test_register_duplicate(mock_session):
    """Weryfikuje: Odrzucenie rejestracji, gdy login/email już istnieje (IntegrityError)."""
    mock_session.commit.side_effect = IntegrityError("Duplicate", params={}, orig=Exception())
    
    response = client.post("/auth/register", json={"username": "dup_user", "password": "password123"})
    
    assert response.status_code == 400
    assert "już istnieje" in response.json()["detail"]
    mock_session.rollback.assert_called_once()


# --- TESTY: /verify-2fa ---

@patch("auth.router_user.pyotp.TOTP.verify")
@patch("auth.router_user.jwt.decode")
def test_verify_2fa_success(mock_jwt_decode, mock_totp_verify, mock_session, mock_user):
    """Weryfikuje: Poprawne potwierdzenie kodu 2FA i wygenerowanie tokenów."""
    mock_jwt_decode.return_value = {"type": "preauth", "sub": "1"}
    mock_user.totp_secret = "SECRET123"
    mock_session.get.return_value = mock_user
    mock_totp_verify.return_value = True

    response = client.post("/auth/verify-2fa", json={"preauth_token": "valid_token", "code": "123456"})
    
    assert response.status_code == 200
    assert "access_token" in response.json()

@patch("auth.router_user.jwt.decode")
def test_verify_2fa_invalid_token(mock_jwt_decode):
    """Weryfikuje: Błąd przy niewłaściwym typie tokena JWT."""
    mock_jwt_decode.return_value = {"type": "wrong_type", "sub": "1"}
    
    response = client.post("/auth/verify-2fa", json={"preauth_token": "bad_token", "code": "123456"})
    assert response.status_code == 401


# --- TESTY: /setup-2fa ---

def test_setup_2fa_success(mock_user, mock_session):
    """Weryfikuje: Wygenerowanie tajnego klucza 2FA i linku URI dla Authenticatora."""
    response = client.post("/auth/setup-2fa")
    
    assert response.status_code == 200
    assert "otpauth_url" in response.json()
    assert "secret_manual" in response.json()
    mock_session.commit.assert_called_once()

def test_setup_2fa_already_enabled(mock_user):
    """Weryfikuje: Odmowę ponownej konfiguracji 2FA, jeśli jest już aktywne."""
    mock_user.totp_enabled = True
    response = client.post("/auth/setup-2fa")
    assert response.status_code == 400


# --- TESTY: /confirm-2fa ---

@patch("auth.router_user.pyotp.TOTP.verify")
def test_confirm_2fa_success(mock_totp_verify, mock_user, mock_session):
    """Weryfikuje: Oficjalną aktywację zabezpieczenia TOTP w profilu użytkownika."""
    mock_user.totp_secret = "SECRET123"
    mock_totp_verify.return_value = True
    
    response = client.post("/auth/confirm-2fa", json={"code": "123456"})
    
    assert response.status_code == 200
    assert mock_user.totp_enabled is True
    mock_session.commit.assert_called_once()

def test_confirm_2fa_no_secret(mock_user):
    """Weryfikuje: Błąd autoryzacji 2FA bez uprzedniego wygenerowania klucza (setup)."""
    mock_user.totp_secret = None
    response = client.post("/auth/confirm-2fa", json={"code": "123456"})
    assert response.status_code == 400


# --- TESTY: /refresh ---

@patch("auth.router_user.jwt.decode")
def test_refresh_token_success(mock_jwt_decode, mock_session, mock_user):
    """Weryfikuje: Pomyślne wydanie nowego tokena dostępu na bazie ważnego refresh tokena."""
    client.cookies.set("refresh_token", "valid_refresh_token")
    mock_session.execute.side_effect = [
        MockResult(None),  # 1szy Select - Sprawdzenie czarnej listy (brak)
        MockResult(mock_user)  # 2gi Select - Pobranie usera na podstawie sub
    ]
    mock_jwt_decode.return_value = {"type": "refresh", "sub": "test_user"}
    
    response = client.post("/auth/refresh")
    
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_refresh_token_blacklisted(mock_session):
    """Weryfikuje: Odrzucenie prośby gdy refresh token jest na czarnej liście (np. wylogowano)."""
    client.cookies.set("refresh_token", "blacklisted_token")
    mock_session.execute.return_value = MockResult(MagicMock(spec=BlacklistedToken))
    
    response = client.post("/auth/refresh")
    
    assert response.status_code == 401
    assert "wykorzystany" in response.json()["detail"]


# --- TESTY: Aktualizacje profilu ---

def test_update_username_success(mock_user, mock_session):
    """Weryfikuje: Poprawną zmianę nazwy użytkownika."""
    mock_session.execute.return_value = MockResult(None) # Brak duplikatu
    
    response = client.put("/auth/update-username", json={"username": "new_name"})
    
    assert response.status_code == 200
    assert mock_user.username == "new_name"
    mock_session.commit.assert_called_once()

def test_update_username_duplicate(mock_user, mock_session):
    """Weryfikuje: Odrzucenie zmiany nazwy użytkownika na już istniejącą w bazie."""
    mock_session.execute.return_value = MockResult(MagicMock()) # Znalazł duplikat
    
    response = client.put("/auth/update-username", json={"username": "taken_name"})
    
    assert response.status_code == 400
    assert "zajęta" in response.json()["detail"]

@patch("auth.router_user.verify_password")
def test_update_password_same_as_old(mock_verify_pwd, mock_user):
    """Weryfikuje: Odrzucenie zmiany hasła w wypadku podania dotychczasowego."""
    mock_verify_pwd.return_value = True # Udaje, że wpisane nowe == stare
    
    response = client.put("/auth/update-password", json={"password": "OldPassword123"})
    
    assert response.status_code == 400
    assert "nie może być takie samo" in response.json()["detail"]

def test_disable_totp_success(mock_user, mock_session):
    """Weryfikuje: Poprawne wyłączenie uwierzytelniania dwuskładnikowego."""
    mock_user.totp_enabled = True
    
    response = client.put("/auth/update-disable-totp")
    
    assert response.status_code == 200
    assert mock_user.totp_enabled is False
    mock_session.commit.assert_called_once()