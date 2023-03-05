from asyncpg import UniqueViolationError
from db import database
from decouple import config
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from managers.auth import ALGORITHM, AuthManager, oauth2_scheme
from models import user
from models.enums import RoleType
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserManager(object):
    @staticmethod
    async def register(user_data: dict):
        user_data["password"] = pwd_context.hash(user_data["password"])
        try:
            id_ = await database.execute(user.insert().values(**user_data))
        except UniqueViolationError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with this email already exists")

        user_do = await database.fetch_one(user.select().where(user.c.id == id_))

        return AuthManager.encode_token(user_do)

    @staticmethod
    async def authenticate_user(email: str, password: str):
        user_do = await UserManager.get_user_by_email(email=email)
        if not user_do:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Wrong email or password")
        if not UserManager.verify_password(password, user_do["password"]):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Wrong email or password")
        return user_do

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def get_user_by_email(email: str):
        user_do = await database.fetch_one(user.select().where(user.c.email == email))
        return user_do

    @staticmethod
    async def get_user_by_id(id_: str):
        user_do = await database.fetch_one(user.select().where(user.c.id == int(id_)))
        return user_do

    @staticmethod
    async def get_current_user(token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, config("SECRET_KEY"), algorithms=[ALGORITHM])  # type: ignore
            user_id = payload.get("sub")  # type: ignore
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        user = await UserManager.get_user_by_id(user_id)
        if user is None:
            raise credentials_exception
        return user

    @staticmethod
    async def get_all_users():
        return await database.fetch_all(user.select())

    @staticmethod
    @database.transaction()
    async def change_role(role: RoleType, user_id: int):
        await database.execute(user.update().where(user.c.id == user_id).values(role=role))


def is_complainer(user=Depends(UserManager.get_current_user)):
    if not user["role"].value == RoleType.complainer.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return user


def is_approver(user=Depends(UserManager.get_current_user)):
    if not user["role"].value == RoleType.approver.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return user


def is_admin(user=Depends(UserManager.get_current_user)):
    if not user["role"].value == RoleType.admin.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return user
