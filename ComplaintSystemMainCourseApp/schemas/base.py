from pydantic import BaseModel


class BaseComplaint(BaseModel):
    title: str
    description: str
    amount: float


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    email: str
