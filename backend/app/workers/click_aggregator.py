import asyncio
import logging
from typing import Counter 

from redis.asyncio import Redis
from sqlalchemy import update, values
from sqlalchemy.ext.asyncio import async_session

from app.redis_client import redis_client
from app.database import async_session
from app.models import Url

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
FLUSH_INTERVAL = 3.0 

async def aggregate_clicks():
    """background_tasks : consumes clicks strams writes to DB in batches"""
    last_id = 0

    while True:
        try:
            response = await redis_client.xread(
                    {"click_stream" : last_id},
                    count= BATCH_SIZE,
                    block= 1000
            )
            _ , messages = response[0]
            if not messages:
                continue

            click_counts=Counter()
            for msg_id, fields in messages:
                last_id= msg_id 
                click_counts[fields["short_code"]] += 1

            if click_counts:
                async with async_session() as session:
                    for code , count in click_counts.items():
                        stmt = ( 
                            update(Url)
                            .where(Url.short_code == code)
                            .values(clicks=Url.clicks + count)
                    )
                        await session.execute(stmt)
                    await session.commit()
            logger.info(f"Flushed {sum(click_counts.values())} clicks for {len(click_counts)} URLs")
        
        except Exception as e :
            logger.error(f"Click aggregator error: {e}")
            await asyncio.sleep(1)  # Backoff on failure

