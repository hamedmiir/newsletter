import asyncio
import click
import logging
from .agents.orchestrator_agent import OrchestratorAgent
from .agents.analytics_agent import AnalyticsAgent

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
def run_analytics():
    """Generate analytics charts from stored data."""
    agent = AnalyticsAgent()
    asyncio.run(agent.run())

if __name__ == "__main__":
    cli()
