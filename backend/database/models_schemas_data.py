from typing import Optional

from sqlmodel import SQLModel, Field


class DataBase(SQLModel):
    data: str

class Data(DataBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=False, index=True, nullable=False)

class DataCreate(DataBase):
    pass

class DataUpdate(DataBase):
    id: int
    data: str

class DataRead(DataBase):
    id: int
    data: str

