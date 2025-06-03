# auto_journalist/publish.py
import click
from .main import run_daily

@click.command()
@click.option('--date', required=False, help='Date for issue (YYYY-MM-DD)')
def publish(date):
    """
    Trigger a manual publication run. The --date flag is currently ignored and kept for compatibility.
    """
    run_daily()

if __name__ == '__main__':
    publish()