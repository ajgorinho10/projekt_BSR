"Punkty końcowe dla użytkowników związane z autentykacją"

import pyotp
from jose import JWTError, jwt

from fastapi import (APIRouter, 
                     HTTPException,
                     Response,
                     Request,
                     Cookie,
                     Query)
from fastapi.params import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from database import User,BlacklistedToken
from database import get_async_session

from .schemas_user import (UserLogin,
                           Verify2FA,
                           UserRead,
                           UserCreate,
                           Confirm2FA,
                           TokenRefreshRequest, UserUpdate)

from .auth_utils import (create_access_token,
                         verify_password,
                         create_preauth_token,
                         get_password_hash,
                         SECRET_KEY,ALGORITHM,
                         create_refresh_token)

from .dependencies_user import get_current_user,require_admin

from .limiter import limiter

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request, 
    user_input: UserLogin, 
    response: Response,
    session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Logowanie użytkowników
    
        Jeśli włączone jest Totp zwracany jest "preauth_token" potwierdzający prawidłowe dane logowania.
        Przeciwnie tokeny dostępu oraz odświerzenia
    """
    statement = select(User).where(User.username == user_input.username)
    result = await session.execute(statement)
    user = result.scalars().first()

    if not user or not verify_password(user_input.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Niepoprawny login lub hasło")

    if user.totp_enabled:
        preauth_token = create_preauth_token(user.id)
        return {
            "step": "2fa_required",
            "preauth_token": preauth_token,
            "message": "Podaj kod z aplikacji uwierzytelniającej"
        }

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False, #False TYLKO podczas testów
        samesite="lax", 
        max_age=7 * 24 * 60 * 60 #7 dni
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout_user(
    response: Response,
    refresh_token: str = Cookie(None),
    session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Wylogowanie użytkowników
    
        Dodaje aktualny refresh_token na listę zablokowanych i usuwa ciasteczko
    """
    statement = select(BlacklistedToken).where(BlacklistedToken.token == refresh_token)
    result = await session.execute(statement)
    print(result)
    if result.scalars().first() is None:
        blacklisted = BlacklistedToken(token=refresh_token)
        session.add(blacklisted)
        await session.commit()
    
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax"
    )
    return {"message": "Wylogowano pomyślnie."}


@router.post("/register", response_model=UserRead)
async def register_user(user_data: UserCreate, session: AsyncSession = Depends(get_async_session)):
    """EndPoint: Rejestracja użytkowników"""
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
@limiter.limit("5/minute")
async def verify_2fa(
    request: Request,
    response: Response,
    data: Verify2FA, 
    session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Weryfikacja kodu Totp
    
        Jeśli kod jest prawidłowy, odsyłamy tokeny dostępu i odświerzenia
    """
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
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False, #False TYLKO podczas testów
        samesite="lax", 
        max_age=7 * 24 * 60 * 60 #7 dni
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/setup-2fa")
async def setup_2fa(
    current_user: User = Depends(get_current_user), 
    session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Ustawienie Totp dla konta
    
        Zwracamy użytkownikowi klucz oraz adres URL.
    """
    
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
async def confirm_2fa(
    data: Confirm2FA, 
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Weryfikacja Totp

        Sprawdzamy czy kod otrzymany od użytkownika jest prawidłowy.
    """
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
        response: Response,
        refresh_token: str = Cookie(None),
        session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Nowy token dostępu
    
        Token odświerzenia się nie zmienia, zwracamy jedynie nowy token dostępowy
    """
    
    if not refresh_token:
         raise HTTPException(status_code=401, detail="Brak tokena odświeżającego.")

    # 1. Sprawdzamy, czy stary token nie został już użyty (Czarna Lista)
    statement = select(BlacklistedToken).where(BlacklistedToken.token == refresh_token)
    result = await session.execute(statement)
    if result.scalars().first():
        raise HTTPException(status_code=401, detail="Ten token został już wykorzystany.")

    # 2. Dekodowanie i weryfikacja JWT
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
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

    # 4. Generowanie NOWYCH tokenów (PAMIĘTAJ O DODANIU ROLI!)
    new_access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.get("/me")
async def test(current_user: User = Depends(get_current_user)):
    """EndPoint: Zwraca dane użytkownika"""
    return current_user


@router.post("/promote-me")
async def promote_to_admin(
        current_user: User = Depends(get_current_user),
        role: str = Query(None),
        session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Zmiana roli użytkownika
    
        Jest to endpoint wprowadzony dla testów aplikacji.
    """
    if role and role == current_user.role and role in ["user","admin"]:
        raise HTTPException(status_code=400, detail="Błędna rola")


    current_user.role = role
    session.add(current_user)
    await session.commit()

    return {
        "message": f"Sukces! Użytkownik {current_user.username} otrzymał rolę 'admin'."
    }

@router.put("/update-username")
async def update_user(
        update_data: UserUpdate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Aktualizuje username użytkownika"""

    update_dict = update_data.model_dump(exclude_unset=True)

    if "username" not in update_dict:
        raise HTTPException(status_code=400, detail="Nie podano nowej nazwy użytkownika do aktualizacji.")

    new_username = update_dict["username"]

    if new_username == current_user.username:
        raise HTTPException(status_code=400, detail="To już jest Twoja nazwa użytkownika!")

    result = await session.execute(select(User).where(User.username == new_username))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(status_code=400, detail="Nazwa użytkownika jest zajęta !")

    current_user.username = new_username
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {
        "message": f"Nazwa użytkownika została zmieniona na: {current_user.username}"
    }


@router.put("/update-password")
async def update_user_password(
        update_data: UserUpdate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Aktualizuje hasło użytkownika"""

    update_dict = update_data.model_dump(exclude_unset=True)

    if "password" not in update_dict:
        raise HTTPException(status_code=400, detail="Nie podano nowego hasła!")

    new_password = update_dict.pop("password")

    if verify_password(new_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Nowe hasło nie może być takie samo jak stare!")

    new_hashed_password = get_password_hash(new_password)

    current_user.hashed_password = new_hashed_password

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {
        "message": "Hasło zostało pomyślnie zaktualizowane!"
    }

@router.put("/update-disable-totp")
async def update_user_disable_totp(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session)
):
    """EndPoint: Wyłączenie Totp"""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400,detail="TOTP 2F nie jest włączone!")

    current_user.totp_enabled = False
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return {
        "message": "TOTP 2F zostało wyłączone!"
    }
