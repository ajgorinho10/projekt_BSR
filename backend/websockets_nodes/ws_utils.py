from jose import jwt, JWTError
from auth import ALGORITHM,SECRET_KEY


async def verify_ws_token_and_role(token: str, allowed_roles: list[str]):
    """Weryfikuje token z URL i sprawdza, czy użytkownik ma odpowiednią rolę"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") == "refresh":
            return None

        user_role = payload.get("role")
        username = payload.get("sub")

        if user_role not in allowed_roles:
            print(f"Odmowa dostępu dla {username}. Rola '{user_role}' nie jest dozwolona.")
            return None

        return username
    except JWTError:
        return None