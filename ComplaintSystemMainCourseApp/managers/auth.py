from datetime import datetime, timedelta

from decouple import config
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class AuthManager(object):
    @staticmethod
    def encode_token(user):
        try:
            payload = {"sub": str(user["id"]), "exp": datetime.now() + timedelta(minutes=120)}
            return jwt.encode(payload, config("SECRET_KEY"), algorithm=ALGORITHM)  # type: ignore
        except Exception:
            raise
