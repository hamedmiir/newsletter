import os
import sqlalchemy as sa
from sqlalchemy import select
from telegram import Bot
from telegram.constants import ParseMode
import datetime

from ..db import get_session
from ..models import User, Preference, Summary, FactCheck, FrequencyEnum, FactStatusEnum
from .base_agent import BaseAgent

class PublisherAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

    async def run(self):
        async for session in get_session():
            users = (await session.execute(sa.select(User))).scalars().all()
            for user in users:
                for pref in user.preferences:
                    now = datetime.datetime.utcnow()
                    last = pref.last_sent
                    if last:
                        elapsed = (now - last).total_seconds()
                        if pref.frequency == FrequencyEnum.HOURLY and elapsed < 3600:
                            continue
                        if pref.frequency == FrequencyEnum.DAILY and elapsed < 86400:
                            continue
                        if pref.frequency == FrequencyEnum.WEEKLY and elapsed < 604800:
                            continue

                    stmt = (
                        select(Summary, FactCheck)
                        .join(FactCheck, FactCheck.summary_id == Summary.id)
                        .where(
                            Summary.topic.ilike(pref.topic),
                            FactCheck.status == FactStatusEnum.VERIFIED
                        )
                        .order_by(Summary.created_at.desc())
                        .limit(5)
                    )
                    rows = (await session.execute(stmt)).all()
                    if not rows:
                        continue

                    messages = []
                    for summary, factcheck in rows:
                        messages.append(
                            f"• {summary.summary_text}\n_Fact:_ {factcheck.status.value}\n"
                        )

                    text = f"Your {pref.frequency.value.title()} News on '{pref.topic}':\n\n" + "\n".join(messages)
                    await self.bot.send_message(
                        chat_id=int(user.telegram_id),
                        text=text,
                        parse_mode=ParseMode.MARKDOWN
                    )

                    pref.last_sent = now
                    await session.commit()