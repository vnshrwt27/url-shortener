from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .routes import redirect, shorten


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="URL Shortener", version="0.1.0", lifespan=lifespan)

app.include_router(shorten.router, prefix="/api")
app.include_router(redirect.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
