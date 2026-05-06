from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column, DateTime
from pydantic import field_validator
import re

class UserBase(SQLModel):
    """Podstawowy model użytkownika po którym dziedziczą inne klasy"""
    username: str = Field(
        unique=True, 
        index=True, 
        nullable=False
    )
    
    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str):
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError("Nazwa użytkownika może zawierać tylko litery, cyfry, kropki, myślniki i podkreślniki.")
        
        if len(v) < 3 or len > 30:
            raise ValueError("Nazwa użytkownika może mieć od 3 do 30 znaków")
        return v

class User(UserBase, table=True):
    """Kompletna tabela użytkownika w bazie, dziedziczy po UserBase"""
    #__table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    role: str = Field(default="user")
    totp_secret: Optional[str] = Field(default=None)
    totp_enabled: bool = Field(default=False)


class BlacklistedToken(SQLModel, table=True):
    """Przechowuje wykorzystane "refresh_token" """
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)

    blacklisted_on: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )