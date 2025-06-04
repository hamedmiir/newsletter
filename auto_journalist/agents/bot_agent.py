import asyncio
from telegram import (
    Update,
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import sqlalchemy as sa
from sqlalchemy import select

from ..db import get_session
from ..models import User, Preference, FrequencyEnum, PlanEnum, UserSource, Source
from .base_agent import BaseAgent
from .source_manager_agent import SourceManagerAgent

(
    MAIN_MENU,
    PLAN_MENU,
    PREF_TOPIC,
    PREF_FREQ,
    MANAGE_MENU,
    ADD_SOURCE_NAME,
    ADD_SOURCE_URL,
    REMOVE_SOURCE_SELECT,
) = range(8)


class BotAgent(BaseAgent):
    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self.app = ApplicationBuilder().token(token).build()

        conv = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                MAIN_MENU: [CallbackQueryHandler(self.main_menu)],
                PLAN_MENU: [CallbackQueryHandler(self.plan_choice)],
                PREF_TOPIC: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.pref_topic)
                ],
                PREF_FREQ: [CallbackQueryHandler(self.pref_frequency)],
                MANAGE_MENU: [CallbackQueryHandler(self.manage_sources)],
                ADD_SOURCE_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.add_source_name
                    )
                ],
                ADD_SOURCE_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_source_url)
                ],
                REMOVE_SOURCE_SELECT: [CallbackQueryHandler(self.remove_source_choice)],
            },
            fallbacks=[CommandHandler("help", self.help)],
        )

        self.app.add_handler(conv)
        self.app.add_handler(CommandHandler("listsources", self.list_sources))
        # legacy command handlers remain for power users
        self.app.add_handler(CommandHandler("plan", self.set_plan))
        self.app.add_handler(CommandHandler("set", self.set_pref))
        self.app.add_handler(CommandHandler("addsource", self.add_source))
        self.app.add_handler(CommandHandler("removesource", self.remove_source))
        self.app.add_handler(CommandHandler("help", self.help))

    async def _send_main_menu(
        self, chat_id: int, bot: Bot, text: str = "Welcome to Auto-Journalist!"
    ):
        keyboard = [
            [InlineKeyboardButton("Set Plan", callback_data="plan")],
            [InlineKeyboardButton("Set Preferences", callback_data="pref")],
            [InlineKeyboardButton("Manage Sources", callback_data="sources")],
            [InlineKeyboardButton("List Sources", callback_data="list")],
            [InlineKeyboardButton("Help", callback_data="help")],
        ]
        await bot.send_message(
            chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

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

        await self._send_main_menu(tg_id, context.bot)
        return MAIN_MENU

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        if data == "plan":
            keyboard = [
                [
                    InlineKeyboardButton("Basic", callback_data="plan_basic"),
                    InlineKeyboardButton("Premium", callback_data="plan_premium"),
                ],
                [InlineKeyboardButton("Back", callback_data="back")],
            ]
            await query.message.reply_text(
                "Choose your plan:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return PLAN_MENU
        if data == "pref":
            await query.message.reply_text("Enter topic:")
            return PREF_TOPIC
        if data == "sources":
            keyboard = [
                [InlineKeyboardButton("Add Source", callback_data="add_source")],
                [InlineKeyboardButton("Remove Source", callback_data="remove_source")],
                [InlineKeyboardButton("Back", callback_data="back")],
            ]
            await query.message.reply_text(
                "Manage sources:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return MANAGE_MENU
        if data == "list":
            await self.list_sources(update, context)
            return MAIN_MENU
        if data == "help":
            await self.help(update, context)
            return MAIN_MENU
        if data == "back":
            await self._send_main_menu(query.message.chat_id, context.bot)
            return MAIN_MENU
        return MAIN_MENU

    async def plan_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == "back":
            await self._send_main_menu(query.message.chat_id, context.bot)
            return MAIN_MENU
        if query.data.startswith("plan_"):
            plan = query.data.split("_", 1)[1]
            context.user_data["plan"] = plan
            await self.set_plan(update, context)
            await self._send_main_menu(
                query.message.chat_id, context.bot, "Plan updated."
            )
            return MAIN_MENU
        return PLAN_MENU

    async def pref_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["topic"] = update.message.text
        keyboard = [
            [InlineKeyboardButton("Hourly", callback_data="freq_hourly")],
            [InlineKeyboardButton("Daily", callback_data="freq_daily")],
            [InlineKeyboardButton("Weekly", callback_data="freq_weekly")],
        ]
        await update.message.reply_text(
            "Choose frequency:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return PREF_FREQ

    async def pref_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == "back":
            await self._send_main_menu(query.message.chat_id, context.bot)
            return MAIN_MENU
        freq = query.data.split("_", 1)[1]
        context.user_data["freq"] = freq
        await self.set_pref(update, context)
        await self._send_main_menu(
            query.message.chat_id, context.bot, "Preference saved."
        )
        return MAIN_MENU

    async def manage_sources(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        if data == "back":
            await self._send_main_menu(query.message.chat_id, context.bot)
            return MAIN_MENU
        if data == "add_source":
            await query.message.reply_text("Enter source name:")
            return ADD_SOURCE_NAME
        if data == "remove_source":
            tg_id = str(query.from_user.id)
            async for session in get_session():
                result = await session.execute(
                    select(User).where(User.telegram_id == tg_id)
                )
                user = result.scalar_one_or_none()
                if not user or user.plan != PlanEnum.PREMIUM:
                    await query.message.reply_text(
                        "Only premium users can remove sources."
                    )
                    return MANAGE_MENU
                custom = [src.source.url for src in user.user_sources]
            if not custom:
                await query.message.reply_text("No custom sources.")
                return MANAGE_MENU
            buttons = [[InlineKeyboardButton(u, callback_data=u)] for u in custom]
            buttons.append([InlineKeyboardButton("Back", callback_data="back")])
            await query.message.reply_text(
                "Select source to remove:", reply_markup=InlineKeyboardMarkup(buttons)
            )
            return REMOVE_SOURCE_SELECT
        return MANAGE_MENU

    async def add_source_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["source_name"] = update.message.text
        await update.message.reply_text("Send source URL:")
        return ADD_SOURCE_URL

    async def add_source_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["source_url"] = update.message.text
        await self.add_source(update, context)
        await self._send_main_menu(
            update.effective_chat.id, context.bot, "Source added."
        )
        return MAIN_MENU

    async def remove_source_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        await query.answer()
        if query.data == "back":
            await self._send_main_menu(query.message.chat_id, context.bot)
            return MAIN_MENU
        context.user_data["remove_url"] = query.data
        await self.remove_source(update, context)
        await self._send_main_menu(
            query.message.chat_id, context.bot, "Source removed."
        )
        return MAIN_MENU

    async def set_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chosen = context.user_data.pop("plan", None)
        if chosen is None:
            args = context.args
            if len(args) != 1 or args[0].lower() not in [p.value for p in PlanEnum]:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="Usage: /plan <basic|premium>",
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
        topic = context.user_data.pop("topic", None)
        freq = context.user_data.pop("freq", None)
        if topic is None or freq is None:
            args = context.args
            if len(args) != 2:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="Usage: /set <topic> <frequency>",
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
        name = context.user_data.pop("source_name", None)
        url = context.user_data.pop("source_url", None)
        if name is None or url is None:
            args = context.args
            if len(args) < 2:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="Usage: /addsource <name> <url>",
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
        url = context.user_data.pop("remove_url", None)
        if url is None:
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

            default_urls = [s["url"] for s in DEFAULT_SOURCES]
            custom_urls = [src.source.url for src in user.user_sources]

            msg = (
                "Default Sources:\n"
                + "\n".join(default_urls)
                + "\n\nYour Sources:\n"
                + ("\n".join(custom_urls) if custom_urls else "None")
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
