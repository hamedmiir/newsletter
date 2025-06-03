import datetime
import sqlalchemy as sa
from sqlalchemy import select
from ..db import get_session
from ..models import Source, UserSource
from sqlalchemy.exc import IntegrityError

class SourceManagerAgent:
    async def add_source(self, user_id: int, name: str, url: str):
        async for session in get_session():
            result = await session.execute(select(Source).where(Source.url == url))
            src = result.scalar_one_or_none()
            if not src:
                src = Source(name=name, url=url, is_social=url.endswith(".rss"), created_at=datetime.datetime.utcnow())
                session.add(src)
                await session.commit()

            try:
                user_src = UserSource(user_id=user_id, source_id=src.id)
                session.add(user_src)
                await session.commit()
            except IntegrityError:
                await session.rollback()

    async def remove_source(self, user_id: int, url: str):
        async for session in get_session():
            result = await session.execute(select(Source).where(Source.url == url))
            src = result.scalar_one_or_none()
            if not src:
                return

            await session.execute(
                sa.delete(UserSource).where(
                    UserSource.user_id == user_id,
                    UserSource.source_id == src.id
                )
            )
            await session.commit()