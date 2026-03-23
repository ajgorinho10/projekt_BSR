from typing import Optional

from pydantic import BaseModel

from database import UserBase

class UserLogin(UserBase):
    password: str

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    username: Optional[str] = None
    totp_enabled: Optional[bool] = None
    password: Optional[str] = None

class UserRead(UserBase):
    id: int
    role: str
    totp_enabled: bool

class Verify2FA(BaseModel):
    preauth_token: str
    code: str

class Confirm2FA(BaseModel):
    code: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str