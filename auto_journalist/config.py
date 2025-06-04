import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NEWS_STREAM_CHANNEL_ID = os.getenv('NEWS_STREAM_CHANNEL_ID')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
PUBLIC_DIR = os.getenv('PUBLIC_DIR', 'public')

# Optional additional sources can be provided via the EXTRA_SOURCES environment
# variable. The format is a semicolon separated list of
# "name|url|is_social" items, for example:
#   EXTRA_SOURCES="Reuters|http://feeds.reuters.com/reuters/topNews|False;HN|https://news.ycombinator.com/rss|True"

DEFAULT_SOURCES = [
    {"name": "BBC", "url": "http://feeds.bbci.co.uk/news/rss.xml", "is_social": False},
    {"name": "CNN", "url": "http://rss.cnn.com/rss/edition.rss", "is_social": False},
    {"name": "Reuters", "url": "http://feeds.reuters.com/reuters/topNews", "is_social": False},
    {"name": "NYTimes", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "is_social": False},
    {"name": "The_Guardian", "url": "https://www.theguardian.com/world/rss", "is_social": False},
    {"name": "Al_Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "is_social": False},
    {"name": "Associated_Press", "url": "https://apnews.com/rss", "is_social": False},
    {"name": "Washington_Post", "url": "http://feeds.washingtonpost.com/rss/national", "is_social": False},
    {"name": "WSJ", "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "is_social": False},
    {"name": "The_Economist", "url": "https://www.economist.com/the-world-this-week/rss.xml", "is_social": False},
    # Example social media RSS (subreddit):
    {"name": "Reddit_technology", "url": "https://www.reddit.com/r/technology/.rss", "is_social": True},
]

def parse_extra_sources():
    sources = []
    raw = os.getenv("EXTRA_SOURCES", "")
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split("|")
        if len(parts) < 2:
            continue
        name, url = parts[0], parts[1]
        is_social = False
        if len(parts) >= 3:
            is_social = parts[2].lower() == "true"
        sources.append({"name": name, "url": url, "is_social": is_social})
    return sources


def get_all_sources():
    """Return the combined list of default and extra sources."""
    return DEFAULT_SOURCES + parse_extra_sources()
