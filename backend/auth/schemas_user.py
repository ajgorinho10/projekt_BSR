from pydantic import BaseModel

from models_user import UserBase

class UserLogin(UserBase):
    password: str

class UserCreate(UserBase):
    password: str

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