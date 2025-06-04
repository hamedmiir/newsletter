import os
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import select
from telegram import Bot
from telegram.constants import ParseMode

from ..db import get_session
from ..models import Summary, FactCheck, Article, StreamItem
from .base_agent import BaseAgent


class NewsStreamAgent(BaseAgent):
    def __init__(self, channel_id: str | None = None):
        super().__init__()
        self.bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
        self.channel_id = channel_id or os.getenv("NEWS_STREAM_CHANNEL_ID")

    def _extract_image(self, raw_json):
        if isinstance(raw_json, dict):
            media = raw_json.get("media_content") or raw_json.get("media_thumbnail")
            if isinstance(media, list) and media:
                return media[0].get("url")
            img = raw_json.get("image")
            if isinstance(img, dict):
                return img.get("href") or img.get("url")
        return None

    async def run(self):
        if not self.channel_id:
            self.logger.error("NEWS_STREAM_CHANNEL_ID not configured")
            return
        async for session in get_session():
            stmt = (
                select(Summary, Article, FactCheck)
                .join(Article, Article.id == Summary.article_id)
                .join(FactCheck, FactCheck.summary_id == Summary.id)
                .outerjoin(StreamItem, StreamItem.summary_id == Summary.id)
                .where(StreamItem.id.is_(None))
                .order_by(Summary.created_at)
            )
            rows = (await session.execute(stmt)).all()
            for summary, article, fact in rows:
                image_url = self._extract_image(article.raw_json)
                text = (
                    f"{summary.summary_text}\n\n"
                    f"Source: {article.source}\n"
                    f"Fact check: {fact.status.value}"
                )
                if image_url:
                    await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=image_url,
                        caption=text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                stream = StreamItem(summary_id=summary.id, sent_at=datetime.utcnow())
                session.add(stream)
                await session.commit()
