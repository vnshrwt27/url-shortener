from pathlib import Path
from typing import AsyncGenerator

from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import ConnectionPool, Redis


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="allow",
    )
    REDIS_URL: str = ""


settings = Settings()

pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    socket_timeout= 5,
    health_check_interval=30
)

redis_client: Redis = Redis(
    connection_pool=pool,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> AsyncGenerator[Redis, None]:
    async with redis_client.client() as connection:
        yield connection
