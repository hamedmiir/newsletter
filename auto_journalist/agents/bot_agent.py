import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sqlalchemy as sa
from sqlalchemy import select

from ..db import get_session
from ..models import User, Preference, FrequencyEnum, PlanEnum, UserSource, Source
from .base_agent import BaseAgent
from .source_manager_agent import SourceManagerAgent

class BotAgent(BaseAgent):
    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self.app = ApplicationBuilder().token(token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("plan", self.set_plan))
        self.app.add_handler(CommandHandler("set", self.set_pref))
        self.app.add_handler(CommandHandler("addsource", self.add_source))
        self.app.add_handler(CommandHandler("removesource", self.remove_source))
        self.app.add_handler(CommandHandler("listsources", self.list_sources))
        self.app.add_handler(CommandHandler("help", self.help))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(select(User).where(User.telegram_id == tg_id))
            user = result.scalar_one_or_none()

            if not user:
                user = User(telegram_id=tg_id, plan=PlanEnum.BASIC)
                session.add(user)
                await session.commit()

            await context.bot.send_message(
                chat_id=tg_id,
                text="Welcome! Use /plan <basic|premium> to select your plan."
            )

    async def set_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) != 1 or args[0].lower() not in [p.value for p in PlanEnum]:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Usage: /plan <basic|premium>"
            )
            return

        chosen = args[0].lower()
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(select(User).where(User.telegram_id == tg_id))
            user = result.scalar_one_or_none()

            if user:
                user.plan = PlanEnum(chosen)
                await session.commit()
                await context.bot.send_message(
                    chat_id=tg_id,
                    text=f"Plan set to '{chosen}'."
                )
            else:
                user = User(telegram_id=tg_id, plan=PlanEnum(chosen))
                session.add(user)
                await session.commit()
                await context.bot.send_message(
                    chat_id=tg_id,
                    text=f"User registered and plan set to '{chosen}'."
                )

    async def set_pref(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) != 2:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Usage: /set <topic> <frequency>"
            )
            return

        topic, freq = args
        if freq.lower() not in [f.value for f in FrequencyEnum]:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Frequency must be one of: hourly, daily, weekly."
            )
            return

        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(select(User).where(User.telegram_id == tg_id))
            user = result.scalar_one_or_none()

            if not user:
                user = User(telegram_id=tg_id, plan=PlanEnum.BASIC)
                session.add(user)
                await session.commit()

            stmt = select(Preference).where(
                Preference.user_id == user.id,
                Preference.topic.ilike(topic)
            )
            pref_result = await session.execute(stmt)
            pref = pref_result.scalar_one_or_none()

            if pref:
                pref.frequency = FrequencyEnum(freq)
            else:
                pref = Preference(user_id=user.id, topic=topic, frequency=FrequencyEnum(freq))
                session.add(pref)

            await session.commit()
            await context.bot.send_message(
                chat_id=tg_id,
                text=f"Preference set: topic='{topic}', frequency='{freq}'."
            )

    async def add_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) < 2:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Usage: /addsource <name> <url>"
            )
            return

        name = args[0]
        url = args[1]
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(select(User).where(User.telegram_id == tg_id))
            user = result.scalar_one_or_none()

            if not user or user.plan != PlanEnum.PREMIUM:
                await context.bot.send_message(
                    chat_id=tg_id,
                    text="Only premium users can add custom sources."
                )
                return

            manager = SourceManagerAgent()
            await manager.add_source(user.id, name, url)
            await context.bot.send_message(
                chat_id=tg_id,
                text=f"Source '{name}' added."
            )

    async def remove_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) != 1:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Usage: /removesource <url>"
            )
            return

        url = args[0]
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(select(User).where(User.telegram_id == tg_id))
            user = result.scalar_one_or_none()

            if not user or user.plan != PlanEnum.PREMIUM:
                await context.bot.send_message(
                    chat_id=tg_id,
                    text="Only premium users can remove sources."
                )
                return

            manager = SourceManagerAgent()
            await manager.remove_source(user.id, url)
            await context.bot.send_message(
                chat_id=tg_id,
                text=f"Source '{url}' removed."
            )

    async def list_sources(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(select(User).where(User.telegram_id == tg_id))
            user = result.scalar_one_or_none()

            if not user:
                await context.bot.send_message(chat_id=tg_id, text="No sources found.")
                return

            from ..config import DEFAULT_SOURCES
            default_urls = [s["url"] for s in DEFAULT_SOURCES]
            custom_urls = [src.source.url for src in user.user_sources]

            msg = "Default Sources:\n" + "\n".join(default_urls) + "\n\nYour Sources:\n" + (
                "\n".join(custom_urls) if custom_urls else "None"
            )
            await context.bot.send_message(chat_id=tg_id, text=msg)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "Commands:\n"
            "/start - Register with the bot\n"
            "/plan <basic|premium> - Choose your plan\n"
            "/set <topic> <frequency> - Set topic (hourly|daily|weekly)\n"
            "/addsource <name> <url> - (Premium) Add custom source\n"
            "/removesource <url> - (Premium) Remove custom source\n"
            "/listsources - List default and your custom sources\n"
            "/help - Show this message"
        )
        await context.bot.send_message(chat_id=update.effective_user.id, text=help_text)

    def run(self):
        self.app.run_polling()