import pytest
from datetime import timedelta
from jose import jwt

from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_preauth_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM
)

def test_password_hashing():
    """Sprawdza poprawność procesu haszowania hasła. Upewnia się, że wynikowy skrót jest niepustym ciągiem znaków i różni się od tekstu jawnego."""
    password = "super_tajne_haslo_123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 0

def test_verify_password_success():
    """Weryfikuje pomyślne logowanie przy użyciu poprawnego hasła. Sprawdza, czy funkcja prawidłowo dopasowuje hasło do jego skrótu."""
    password = "super_tajne_haslo_123"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True

def test_verify_password_fail():
    """Testuje zachowanie systemu przy podaniu błędnego hasła. Upewnia się, że funkcja weryfikująca stanowczo odrzuca niepasujące dane."""
    password = "super_tajne_haslo_123"
    hashed = get_password_hash(password)
    
    assert verify_password("bledne_haslo", hashed) is False

def test_create_access_token_default_expiry():
    """Weryfikuje generowanie głównego tokena JWT ze standardowym czasem wygaśnięcia. Sprawdza, czy zakodowane w nim dane (np. rola) są poprawnie zachowane."""
    data = {"sub": "testuser", "role": "admin"}
    token = create_access_token(data)
    
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert decoded.get("sub") == "testuser"
    assert decoded.get("role") == "admin"
    assert "exp" in decoded

def test_create_access_token_custom_expiry():
    """Testuje tworzenie głównego tokena JWT z niestandardowym czasem ważności. Potwierdza, że system elastycznie reaguje na zmianę terminu wygaśnięcia."""
    data = {"sub": "testuser"}
    custom_expiry = timedelta(minutes=15)
    token = create_access_token(data, expires_delta=custom_expiry)
    
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert decoded.get("sub") == "testuser"
    assert "exp" in decoded

def test_create_preauth_token():
    """Sprawdza generowanie tymczasowego tokena dla procesu dwuetapowej autoryzacji (2FA). Upewnia się, że token posiada prawidłowy typ docelowy i przypisany identyfikator."""
    user_id = 99
    token = create_preauth_token(user_id)
    
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert decoded.get("sub") == str(user_id)
    assert decoded.get("type") == "preauth"
    assert "exp" in decoded

def test_create_refresh_token():
    """Weryfikuje tworzenie długowiecznego tokena odświeżającego sesję. Oczekuje, że wygenerowany obiekt JWT będzie posiadał odpowiedni znacznik typu 'refresh'."""
    data = {"sub": "testuser"}
    token = create_refresh_token(data)
    
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert decoded.get("sub") == "testuser"
    assert decoded.get("type") == "refresh"
    assert "exp" in decoded