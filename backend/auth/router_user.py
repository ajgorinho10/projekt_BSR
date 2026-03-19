import pyotp
from jose import JWTError, jwt

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from models_user import User,BlacklistedToken
from db import get_async_session

from .schemas_user import (UserLogin,
                           Verify2FA,
                           UserRead,
                           UserCreate,
                           Confirm2FA,
                           TokenRefreshRequest)

from .auth_utils import (create_access_token,
                         verify_password,
                         create_preauth_token,
                         get_password_hash,
                         SECRET_KEY,ALGORITHM,
                         create_refresh_token)

from .dependencies_user import get_current_user,require_admin

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/login")
async def login(user_input: UserLogin, session: AsyncSession = Depends(get_async_session)):
    statement = select(User).where(User.username == user_input.username)
    result = await session.execute(statement)
    user = result.scalars().first()

    if not user or not verify_password(user_input.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Niepoprawny login lub hasło")

    if user.totp_enabled:
        # TWORZYMY TYMCZASOWY TOKEN
        preauth_token = create_preauth_token(user.id)
        return {
            "step": "2fa_required",
            "preauth_token": preauth_token, # Wysyłamy go klientowi
            "message": "Podaj kod z aplikacji uwierzytelniającej"
        }

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # Zwracamy nowy token!
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout_user():
    return {"message": "Hello World"}


@router.post("/register", response_model=UserRead)
async def register_user(user_data: UserCreate, session: AsyncSession = Depends(get_async_session)):
    # 1. Haszowanie hasła
    hashed_pwd = get_password_hash(user_data.password)

    new_user = User(
        username=user_data.username,
        hashed_password=hashed_pwd,
    )

    session.add(new_user)

    try:
        await session.commit()
        await session.refresh(new_user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Użytkownik o takim loginie lub emailu już istnieje.")

    return new_user


@router.post("/verify-2fa")
async def verify_2fa(data: Verify2FA, session: AsyncSession = Depends(get_async_session)):

    try:
        payload = jwt.decode(data.preauth_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "preauth":
            raise HTTPException(status_code=401, detail="Nieprawidłowy typ tokena")

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Błąd tokena")

        user_id = int(user_id_str)
    except JWTError:
        raise HTTPException(status_code=401, detail="Sesja logowania wygasła. Zaloguj się ponownie.")


    user = await session.get(User, user_id)
    if not user or not user.totp_secret:
        raise HTTPException(status_code=404, detail="Błąd weryfikacji 2FA")


    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Błędny kod 2FA")

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # Zwracamy nowy token!
        "token_type": "bearer"
    }


@router.post("/setup-2fa")
async def setup_2fa(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA jest już aktywne na tym koncie.")

    secret = pyotp.random_base32()

    current_user.totp_secret = secret
    session.add(current_user)
    await session.commit()

    totp = pyotp.TOTP(secret)
    provisioning_url = totp.provisioning_uri(
        name=current_user.username,
        issuer_name="Bully Cluster"
    )

    return {"otpauth_url": provisioning_url, "secret_manual": secret}


@router.post("/confirm-2fa")
async def confirm_2fa(data: Confirm2FA, current_user: User = Depends(get_current_user),
                      session: AsyncSession = Depends(get_async_session)):
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA jest już włączone.")

    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Najpierw wygeneruj kod QR w /setup-2fa.")

    # Sprawdzamy kod
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Błędny kod autoryzacyjny. Spróbuj ponownie.")

    # Jeśli kod jest poprawny, oficjalnie aktywujemy 2FA!
    current_user.totp_enabled = True
    session.add(current_user)
    await session.commit()

    return {"message": "Autoryzacja dwuetapowa została pomyślnie aktywowana!"}


@router.post("/refresh")
async def refresh_token(
        data: TokenRefreshRequest,
        session: AsyncSession = Depends(get_async_session)):  # Usunięto Depends(get_current_user)!

    # 1. Sprawdzamy, czy stary token nie został już użyty (Czarna Lista)
    statement = select(BlacklistedToken).where(BlacklistedToken.token == data.refresh_token)
    result = await session.execute(statement)
    if result.scalars().first():
        raise HTTPException(status_code=401, detail="Ten token został już wykorzystany.")

    # 2. Dekodowanie i weryfikacja JWT
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Nieprawidłowy typ tokena")

        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Błąd tokena")
    except JWTError:
        raise HTTPException(status_code=401, detail="Nieważny token odświeżający.")

    # 3. POBRANIE UŻYTKOWNIKA RĘCZNIE NA PODSTAWIE TOKENA
    statement = select(User).where(User.username == username)
    result = await session.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")

    # 4. SPALENIE STAREGO TOKENA (Zapis do bazy)
    blacklisted = BlacklistedToken(token=data.refresh_token)
    session.add(blacklisted)

    # 5. Generowanie NOWYCH tokenów (PAMIĘTAJ O DODANIU ROLI!)
    new_access_token = create_access_token(data={"sub": user.username, "role": user.role})
    new_refresh_token = create_refresh_token(data={"sub": user.username})

    await session.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.get("/me")
async def test(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/promote-me")
async def promote_to_admin(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):

    if current_user.role == "admin":
        raise HTTPException(status_code=400, detail="Jesteś już administratorem.")

    current_user.role = "admin"
    session.add(current_user)
    await session.commit()

    return {
        "message": f"Sukces! Użytkownik {current_user.username} otrzymał rolę 'admin'."
    }

@router.get("/admin")
async def admin(current_user: User = Depends(require_admin)):
    return current_user