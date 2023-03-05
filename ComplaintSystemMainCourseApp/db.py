import contextlib

import databases
import sqlalchemy
from decouple import config

DATABASE_URL = f"postgresql+asyncpg://{config('DB_USER')}:{config('DB_PASSWORD')}@postgres:5432/complaints"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()


@contextlib.contextmanager  # type: ignore
async def transaction():
    transaction = await database.transaction()
    try:
        yield
    except Exception:
        await transaction.rollback()
    else:
        await transaction.commit()
