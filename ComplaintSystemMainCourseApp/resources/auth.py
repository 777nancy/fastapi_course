from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from managers.auth import AuthManager
from managers.user import UserManager
from schemas.base import Token
from schemas.request.user import UserRegisterIn

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegisterIn):
    token = await UserManager.register(user_data.dict())

    return {"access_token": token}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await UserManager.authenticate_user(email=form_data.username, password=form_data.password)
    token = AuthManager.encode_token(user)
    return {"access_token": token}
