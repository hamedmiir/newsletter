import feedparser
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from .base_agent import BaseAgent
from ..db import get_session
from ..models import Article, User, PlanEnum

class CrawlerAgent(BaseAgent):
    def __init__(self, sources=None):
        super().__init__()
        self.sources_override = sources

    async def fetch_feed(self, url):
        return feedparser.parse(url)

    async def run(self):
        async for session in get_session():
            # Gather configured sources
            sources = []
            if self.sources_override is not None:
                active_sources = self.sources_override
            else:
                from ..config import get_all_sources
                active_sources = get_all_sources()
            for s in active_sources:
                sources.append({"name": s["name"], "url": s["url"]})

            # Add user‐specific sources for premium users
            result = await session.execute(sa.select(User))
            users = result.scalars().all()
            for user in users:
                if user.plan == PlanEnum.PREMIUM:
                    for src in user.sources:
                        sources.append({"name": src.name, "url": src.url})

            # Deduplicate by URL
            seen = set()
            final_sources = []
            for s in sources:
                if s["url"] not in seen:
                    seen.add(s["url"])
                    final_sources.append(s)

            # Fetch each feed
            for src in final_sources:
                feed_url = src["url"]
                self.logger.info(f"Fetching feed: {feed_url}")
                feed = await self.fetch_feed(feed_url)
                for entry in feed.entries:
                    article_url = entry.link
                    try:
                        article = Article(
                            url=article_url,
                            source=src["name"],
                            raw_json=entry,
                            fetched_at=datetime.utcnow()
                        )
                        session.add(article)
                        await session.commit()
                    except IntegrityError:
                        await session.rollback()
                        self.logger.debug(f"Duplicate skipped: {article_url}")
