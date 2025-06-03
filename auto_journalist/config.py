import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
PUBLIC_DIR = os.getenv('PUBLIC_DIR', 'public')
DEFAULT_SOURCES = [
    {'name': 'BBC', 'url': 'http://feeds.bbci.co.uk/news/rss.xml', 'is_social': False},
    {'name': 'CNN', 'url': 'http://rss.cnn.com/rss/edition.rss', 'is_social': False},
    # Example social media RSS (subreddit):
    {'name': 'Reddit_technology', 'url': 'https://www.reddit.com/r/technology/.rss', 'is_social': True},
]