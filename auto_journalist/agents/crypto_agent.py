import os
import sqlalchemy as sa
from telegram import Bot
from telegram.constants import ParseMode

from .base_agent import BaseAgent
from ..db import get_session
from ..models import Summary, Article
from ..config import CRYPTO_SOURCES, CRYPTO_TELEGRAM_CHAT_ID


class CryptoTrendAgent(BaseAgent):
    """Analyze crypto-related news summaries and post a trend prediction."""

    def __init__(self, model_name: str = "gpt-4o") -> None:
        super().__init__()
        self.model = model_name
        self.source_names = {s["name"] for s in CRYPTO_SOURCES}
        token = os.getenv("TELEGRAM_TOKEN")
        self.bot = Bot(token=token) if token and CRYPTO_TELEGRAM_CHAT_ID else None

    async def run(self) -> None:
        async for session in get_session():
            stmt = (
                sa.select(Summary.summary_text)
                .join(Article, Article.id == Summary.article_id)
                .where(Article.source.in_(self.source_names))
                .order_by(Summary.created_at.desc())
                .limit(10)
            )
            rows = (await session.execute(stmt)).scalars().all()
            if not rows:
                return

            prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are an analyst using news sentiment as a non-technical indicator "
                        "for cryptocurrency markets. Provide a short prediction of near-term "
                        "market direction and any notable signals.",
                    ),
                },
                {"role": "user", "content": "\n\n".join(rows)},
            ]
            response = await self.call_openai(
                model=self.model,
                messages=prompt,
                max_tokens=200,
            )
            if response is None:
                return

            analysis = response.choices[0].message.content
            if self.bot:
                await self.bot.send_message(
                    chat_id=int(CRYPTO_TELEGRAM_CHAT_ID),
                    text=analysis,
                    parse_mode=ParseMode.MARKDOWN,
                )

