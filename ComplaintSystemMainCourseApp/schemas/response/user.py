from models.enums import RoleType
from pydantic import BaseModel
from schemas.base import UserBase


class UserOut(UserBase):
    id: int
    first_name: str
    last_name: str
    phone: str
    role: RoleType
    iban: str
