import enum
import py_compile
from datetime import datetime, timedelta
from typing import Optional
from wsgiref.validate import validator

import databases
import jwt
import sqlalchemy
from decouple import config
from email_validator import EmailNotValidError
from email_validator import validate_email as validate_e
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, validator
from starlette.requests import Request
from typing_extensions import deprecated

DATABASE_URL = f"postgresql://{config('DB_USER')}:{config('DB_PASSWORD')}@postgres:5432/clothes"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()


class UserRole(enum.Enum):
    super_admin = "super admin"
    admin = "admin"
    user = "user"


users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("email", sqlalchemy.String(120), unique=True),
    sqlalchemy.Column("password", sqlalchemy.String(255)),
    sqlalchemy.Column("full_name", sqlalchemy.String(200)),
    sqlalchemy.Column("phone", sqlalchemy.String(13)),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column(
        "last_modified_at",
        sqlalchemy.DateTime,
        nullable=False,
        server_default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
    ),
    sqlalchemy.Column("role", sqlalchemy.Enum(UserRole), nullable=False, server_default=UserRole.user.name),
)


class ColorEnum(enum.Enum):
    pink = "pink"
    black = "black"
    white = "white"
    yellow = "yellow"


class SizeEnum(enum.Enum):
    xs = "xs"
    s = "s"
    m = "m"
    l = "l"
    xl = "xl"
    xxl = "xxl"


clothes = sqlalchemy.Table(
    "clothes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String(120), unique=True),
    sqlalchemy.Column("color", sqlalchemy.Enum(ColorEnum), nullable=False),
    sqlalchemy.Column("size", sqlalchemy.Enum(SizeEnum), nullable=False),
    sqlalchemy.Column("photo_url", sqlalchemy.String(255)),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(), nullable=False, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column(
        "last_modified_at",
        sqlalchemy.DateTime,
        nullable=False,
        server_default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
    ),
)


class EmailField(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            validate_e(v)
            return v
        except EmailNotValidError:
            return ValueError("Email is not valid")


class BaseUser(BaseModel):
    email: EmailField
    full_name: str

    @validator("full_name")
    def validate_full_name(cls, v):
        try:
            first_name, last_name = v.split()
            return v
        except EmailNotValidError:
            return ValueError("You should provide at least 2 names")


class UserSignIn(BaseUser):
    password: str


class UserSignOut(BaseModel):
    phone: Optional[str]
    created_at: datetime
    last_modified_at: datetime


app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CustomHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request):
        res = await super().__call__(request)
        try:
            payload = jwt.decode(res.credentials, config("JWT_SECRET"), algorithms=["HS256"])
            user = await database.fetch_one(users.select().where(users.c.id == payload["sub"]))
            request.state.user = user
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token is expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "invalid Token")


oauth_schema = CustomHTTPBearer()


def is_admin(request: Request):
    user = request.state.user
    if not (user and user["role"] in (UserRole.super_admin, UserRole.admin)):
        raise HTTPException(403, "You do not have permission for this resource")


def create_access_token(user):
    try:
        payload = {"sub": user.id, "exp": datetime.now() + timedelta(minutes=120)}
        return jwt.encode(payload, config("JWT_SECRET"), algorithm="HS256")
    except Exception as ex:
        raise ex


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/register/", status_code=201)  # , response_model=UserSignOut)
async def create_user(user: UserSignIn):
    user.password = pwd_context.hash(user.password)
    q = users.insert().values(**user.dict())
    id = await database.execute(q)
    created_user = await database.fetch_one(users.select().where(users.c.id == id))
    taken = create_access_token(created_user)
    return {"token": taken}


class ClothesBase(BaseModel):
    name: str
    size: SizeEnum
    color: ColorEnum


class ClothesIn(ClothesBase):
    pass


class ClothesOut(ClothesBase):
    id: int
    created_at: datetime
    last_modified_at: datetime


@app.post(
    "/clothes/", response_model=ClothesOut, dependencies=[Depends(oauth_schema), Depends(is_admin)], status_code=201
)
async def create_clothes(clothes_data: ClothesIn):
    id = await database.execute(clothes.insert().values(**clothes_data))
    return await database.fetch_one(clothes.select().where(clothes.c.id == id))


@app.get("/clothes/", dependencies=[Depends(oauth_schema)])
async def get_all_clothes():
    return await database.fetch_all(clothes.select())
