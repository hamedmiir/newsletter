import asyncio
import click
import logging
from .agents.orchestrator_agent import OrchestratorAgent
from .agents.analytics_agent import AnalyticsAgent
from .agents.crypto_orchestrator import CryptoOrchestrator
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

@click.group()
def cli():
    pass

@cli.command()
def run_daily():
    orchestrator = OrchestratorAgent()
    asyncio.run(orchestrator.run_daily())

@cli.command()
def run_bot():
    orchestrator = OrchestratorAgent()
    orchestrator.run_bot()

@cli.command()
def run_stream():
    orchestrator = OrchestratorAgent()
    asyncio.run(orchestrator.run_stream())
@cli.command()
def run_crypto_hourly():
    """Run the crypto news analysis every hour and post to Telegram."""
    orchestrator = CryptoOrchestrator()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(orchestrator.run_once, "interval", hours=1)
    scheduler.start()
    asyncio.get_event_loop().run_until_complete(orchestrator.run_once())
    asyncio.get_event_loop().run_forever()
@cli.command()
def run_analytics():
    """Generate analytics charts from stored data."""
    agent = AnalyticsAgent()
    asyncio.run(agent.run())


if __name__ == '__main__':
    cli()
