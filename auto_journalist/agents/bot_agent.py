from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sqlalchemy import select

from ..db import get_session
from ..models import User, Preference, FrequencyEnum, PlanEnum, UserSource, Source
from .base_agent import BaseAgent
from .source_manager_agent import SourceManagerAgent
from .factcheck_agent import FactCheckAgent


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
        self.app.add_handler(CommandHandler("verify", self.verify))
        self.app.add_handler(CommandHandler("help", self.help))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(
                select(User).where(User.telegram_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(telegram_id=tg_id, plan=PlanEnum.BASIC)
                session.add(user)
                await session.commit()

            await context.bot.send_message(
                chat_id=tg_id,
                text="Welcome! Use /plan <basic|premium> to select your plan.",
            )

    async def set_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) != 1 or args[0].lower() not in [p.value for p in PlanEnum]:
            await context.bot.send_message(
                chat_id=update.effective_user.id, text="Usage: /plan <basic|premium>"
            )
            return

        chosen = args[0].lower()
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(
                select(User).where(User.telegram_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.plan = PlanEnum(chosen)
                await session.commit()
                await context.bot.send_message(
                    chat_id=tg_id, text=f"Plan set to '{chosen}'."
                )
            else:
                user = User(telegram_id=tg_id, plan=PlanEnum(chosen))
                session.add(user)
                await session.commit()
                await context.bot.send_message(
                    chat_id=tg_id, text=f"User registered and plan set to '{chosen}'."
                )

    async def set_pref(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) != 2:
            await context.bot.send_message(
                chat_id=update.effective_user.id, text="Usage: /set <topic> <frequency>"
            )
            return

        topic, freq = args
        if freq.lower() not in [f.value for f in FrequencyEnum]:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Frequency must be one of: hourly, daily, weekly.",
            )
            return

        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(
                select(User).where(User.telegram_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(telegram_id=tg_id, plan=PlanEnum.BASIC)
                session.add(user)
                await session.commit()

            stmt = select(Preference).where(
                Preference.user_id == user.id, Preference.topic.ilike(topic)
            )
            pref_result = await session.execute(stmt)
            pref = pref_result.scalar_one_or_none()

            if pref:
                pref.frequency = FrequencyEnum(freq)
            else:
                pref = Preference(
                    user_id=user.id, topic=topic, frequency=FrequencyEnum(freq)
                )
                session.add(pref)

            await session.commit()
            await context.bot.send_message(
                chat_id=tg_id,
                text=f"Preference set: topic='{topic}', frequency='{freq}'.",
            )

    async def add_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) < 2:
            await context.bot.send_message(
                chat_id=update.effective_user.id, text="Usage: /addsource <name> <url>"
            )
            return

        name = args[0]
        url = args[1]
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(
                select(User).where(User.telegram_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if not user or user.plan != PlanEnum.PREMIUM:
                await context.bot.send_message(
                    chat_id=tg_id, text="Only premium users can add custom sources."
                )
                return

            manager = SourceManagerAgent()
            await manager.add_source(user.id, name, url)
            await context.bot.send_message(
                chat_id=tg_id, text=f"Source '{name}' added."
            )

    async def remove_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if len(args) != 1:
            await context.bot.send_message(
                chat_id=update.effective_user.id, text="Usage: /removesource <url>"
            )
            return

        url = args[0]
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(
                select(User).where(User.telegram_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if not user or user.plan != PlanEnum.PREMIUM:
                await context.bot.send_message(
                    chat_id=tg_id, text="Only premium users can remove sources."
                )
                return

            manager = SourceManagerAgent()
            await manager.remove_source(user.id, url)
            await context.bot.send_message(
                chat_id=tg_id, text=f"Source '{url}' removed."
            )

    async def list_sources(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_id = str(update.effective_user.id)
        async for session in get_session():
            result = await session.execute(
                select(User).where(User.telegram_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                await context.bot.send_message(chat_id=tg_id, text="No sources found.")
                return

            from ..config import DEFAULT_SOURCES

            default_list = [f"{s['name']} - {s['url']}" for s in DEFAULT_SOURCES]

            stmt = (
                select(Source.name, Source.url)
                .join(UserSource)
                .where(UserSource.user_id == user.id)
            )
            result = await session.execute(stmt)
            custom_list = [f"{name} - {url}" for name, url in result.all()]

            msg = (
                "Default Sources:\n"
                + "\n".join(default_list)
                + "\n\nYour Sources:\n"
                + ("\n".join(custom_list) if custom_list else "None")
                + "\n\nUse /addsource <name> <rss url> to add a new feed."
            )
            await context.bot.send_message(chat_id=tg_id, text=msg)

    async def verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await context.bot.send_message(
                chat_id=update.effective_user.id, text="Usage: /verify <url or text>"
            )
            return

        query = " ".join(context.args)
        if query.startswith("http://") or query.startswith("https://"):
            try:
                from newspaper import Article

                article = Article(query)
                article.download()
                article.parse()
                text = article.text
            except Exception as e:
                self.logger.error(f"Article extraction failed: {e!r}")
                try:
                    import requests

                    resp = requests.get(query, timeout=10)
                    resp.raise_for_status()
                    text = resp.text
                except Exception:
                    await context.bot.send_message(
                        chat_id=update.effective_user.id,
                        text="Unable to fetch that link.",
                    )
                    return
        else:
            text = query

        text = text[:2000]
        fc = FactCheckAgent()
        status, citations, analysis = await fc.fact_check_text(text)
        message = f"Fact-check status: {status.value}\n{analysis}"
        if citations:
            message += "\nSources:\n" + "\n".join(citations)
        await context.bot.send_message(chat_id=update.effective_user.id, text=message)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "Commands:\n"
            "/start - Register with the bot\n"
            "/plan <basic|premium> - Choose your plan\n"
            "/set <topic> <frequency> - Set topic (hourly|daily|weekly)\n"
            "/addsource <name> <url> - (Premium) Add custom source\n"
            "/removesource <url> - (Premium) Remove custom source\n"
            "/listsources - List default and your custom sources\n"
            "/verify <url|text> - Check a news link or snippet\n"
            "A source URL is an RSS or social feed like https://rss.cnn.com/rss/edition.rss\n"
            "/help - Show this message"
        )
        await context.bot.send_message(chat_id=update.effective_user.id, text=help_text)

    def run(self):
        self.app.run_polling()
