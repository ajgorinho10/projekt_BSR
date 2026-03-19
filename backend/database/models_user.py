from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column, DateTime


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, nullable=False)

class User(UserBase, table=True):
    #__table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    role: str = Field(default="user")
    totp_secret: Optional[str] = Field(default=None)
    totp_enabled: bool = Field(default=False)


class BlacklistedToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)

    blacklisted_on: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )