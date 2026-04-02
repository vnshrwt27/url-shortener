from __future__ import annotations

from typing import Final

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Url
from ..redis_client import get_redis

router = APIRouter(tags=["redirect"])

CACHE_TTL_SECONDS: Final[int] = 60 * 60 * 24


@router.get("/{code}", response_class=RedirectResponse)
async def redirect_short_url(
    code: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> RedirectResponse:
    cached_url = await redis.get(code)

    if cached_url is None:
        result = await db.execute(select(Url).where(Url.short_code == code))
        url_entry = result.scalar_one_or_none()
        if url_entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found.")
        target_url = url_entry.original_url
        await redis.setex(code, CACHE_TTL_SECONDS, target_url)
    else:
        target_url = cached_url

    click_stmt = (
        update(Url)
        .where(Url.short_code == code)
        .values(clicks=Url.clicks + 1)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(click_stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found.")

    await db.commit()

    return RedirectResponse(url=target_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
