from __future__ import annotations

import secrets
import string
from typing import Final

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Url
from ..redis_client import get_redis
from ..schemas import UrlCreate, UrlResponse

router = APIRouter(prefix="/shorten", tags=["shorten"])

CACHE_TTL_SECONDS: Final[int] = 60 * 60 * 24
SHORT_CODE_LENGTH: Final[int] = 7
MAX_CUSTOM_CODE_LENGTH: Final[int] = 10
MAX_GENERATION_ATTEMPTS: Final[int] = 5
ALLOWED_CHARACTERS: Final[str] = string.ascii_letters + string.digits


def _generate_candidate_code(length: int = SHORT_CODE_LENGTH) -> str:
    return "".join(secrets.choice(ALLOWED_CHARACTERS) for _ in range(length))


async def _generate_unique_short_code(db: AsyncSession, custom_code: str | None) -> str:
    if custom_code:
        normalized_code = custom_code.strip()
        if not normalized_code or len(normalized_code) > MAX_CUSTOM_CODE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Custom code must be 1-10 characters.",
            )
        if any(ch not in ALLOWED_CHARACTERS for ch in normalized_code):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Custom code must be alphanumeric.",
            )

        exists_stmt = select(Url.id).where(Url.short_code == normalized_code)
        result = await db.execute(exists_stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Custom code already in use.",
            )
        return normalized_code

    for _ in range(MAX_GENERATION_ATTEMPTS):
        candidate = _generate_candidate_code()
        exists_stmt = select(Url.id).where(Url.short_code == candidate)
        result = await db.execute(exists_stmt)
        if result.scalar_one_or_none() is None:
            return candidate

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate unique short code. Please retry.",
    )


@router.post("/", response_model=UrlResponse, status_code=status.HTTP_201_CREATED)
async def create_short_url(
    payload: UrlCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Url:
    short_code = await _generate_unique_short_code(db, payload.custom_code)

    url_entry = Url(short_code=short_code, original_url=str(payload.url))
    db.add(url_entry)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Short code already exists.",
        ) from exc

    await db.refresh(url_entry)
    await redis.setex(short_code, CACHE_TTL_SECONDS, url_entry.original_url)

    return url_entry
