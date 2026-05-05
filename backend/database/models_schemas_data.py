from typing import Optional

from sqlmodel import SQLModel, Field


class DataBase(SQLModel):
    """Podstawowy model po którym dziedziczą inne klasy"""
    data: str


class Data(DataBase, table=True):
    """ Każde dane od użytkownika muszą zawierać unikalne id oraz właściciela(username)"""
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

