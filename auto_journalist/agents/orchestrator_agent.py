from .crawler_agent import CrawlerAgent
from .summarizer_agent import SummarizerAgent
from .factcheck_agent import FactCheckAgent
from .commentary_agent import CommentaryAgent
from .formatter_agent import FormatterAgent
from .publisher_agent import PublisherAgent
from .news_stream_agent import NewsStreamAgent
from .bot_agent import BotAgent
from .base_agent import BaseAgent

import os

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.crawler = CrawlerAgent()
        self.summarizer = SummarizerAgent()
        self.factchecker = FactCheckAgent()
        self.commentator = CommentaryAgent()
        self.formatter = FormatterAgent()
        self.publisher = PublisherAgent()
        self.streamer = NewsStreamAgent()

        # The BotAgent requires the Telegram token from the environment
        telegram_token = os.getenv("TELEGRAM_TOKEN", "")
        self.bot_agent = BotAgent(telegram_token)

    async def run_daily(self):
        """
        Run the entire daily pipeline:
        1. Crawl new articles
        2. Summarize them
        3. Fact-check
        4. Add commentary
        5. Format into newsletter
        6. Publish via Telegram
        Finally, close any shared OpenAI sessions.
        """
        await self.crawler.run()
        await self.summarizer.run()
        await self.factchecker.run()
        await self.commentator.run()
        await self.formatter.run()
        await self.publisher.run()

        # Close the shared OpenAI session (so no unclosed client session warnings)
        await self.close()

    async def run_stream(self):
        """Fetch new articles and immediately publish them to the news stream."""
        await self.crawler.run()
        await self.summarizer.run()
        await self.factchecker.run()
        await self.streamer.run()
        await self.close()

    def run_bot(self):
        """
        Start the Telegram bot loop. This is synchronous (long-running loop),
        so we don't use `await` here. BotAgent.run() handles polling internally.
        """
        self.bot_agent.run()
