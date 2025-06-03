import asyncio
import click
import logging
from .agents.orchestrator_agent import OrchestratorAgent

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

if __name__ == '__main__':
    cli()