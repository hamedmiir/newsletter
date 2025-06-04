from .crawler_agent import CrawlerAgent
from .summarizer_agent import SummarizerAgent
from .crypto_agent import CryptoTrendAgent
from .base_agent import BaseAgent
from ..config import CRYPTO_SOURCES


class CryptoOrchestrator(BaseAgent):
    """Pipeline orchestrator dedicated to crypto news analysis."""

    def __init__(self) -> None:
        super().__init__()
        self.crawler = CrawlerAgent(sources=CRYPTO_SOURCES)
        self.summarizer = SummarizerAgent()
        self.crypto_agent = CryptoTrendAgent()

    async def run_once(self) -> None:
        await self.crawler.run()
        await self.summarizer.run()
        await self.crypto_agent.run()
        await self.close()

