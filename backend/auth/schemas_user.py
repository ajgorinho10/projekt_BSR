"""Schematy dla użytkowników"""

from typing import Optional
from pydantic import BaseModel, Field
from database import UserBase
from pydantic import field_validator
import re

class UserLogin(UserBase):
    password: str = Field(min_length=1)

class UserCreate(UserBase):
    password: str = Field(
        description="Hasło musi mieć od 8 do 30 znaków",
    )
    
    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str):
        if len(v) < 8 or len(v) > 30:
            raise ValueError("Hasło musi mieć od 8 do 30 znaków")
        return v

class UserUpdate(UserBase):
    username: Optional[str] = Field(
        default=None, 
        min_length=3, 
        max_length=30, 
        pattern=r"^[a-zA-Z0-9_.-]+$"
    )
    totp_enabled: Optional[bool] = None
    password: Optional[str] = Field(
        default=None, 
        min_length=8, 
        max_length=128
    ) 

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