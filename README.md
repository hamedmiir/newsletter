# README.md

Auto-Journalist is a modular, multi-agent system that crawls news sources (including social feeds), summarizes articles with GPT, fact-checks against Wikipedia, adds contextual commentary, and delivers personalized updates via Telegram. Users register through the Telegram bot, set topics and frequency, and (with a premium plan) manage custom RSS or social sources.

## Features

* **User Plans**: Basic (default sources) and Premium (add custom sources).
* **Source Management**: `/listsources`, `/addsource <name> <url>`, `/removesource <url>` with inline prompts and default RSS suggestions.
* **Preferences**: `/set <topic> <frequency>` (hourly, daily, weekly).
* **Multi-Agent Pipeline**:

  * **CrawlerAgent**: Fetches RSS and social feeds.
  * **SummarizerAgent**: Uses OpenAI to generate bullet-point summaries.
  * **FactCheckAgent**: Verifies summaries via Wikipedia.
  * **CommentaryAgent**: Adds one-paragraph context via OpenAI.
  * **FormatterAgent**: Renders Markdown & HTML for archival.
  * **PublisherAgent**: Sends personalized messages to Telegram users.
* **Dockerized**: Run everything in containers with `docker-compose`.
* **Database**: PostgreSQL stores articles, summaries, fact-checks, commentary, users, preferences, and sources.
* **Interactive Bot UI**: Telegram bot now uses inline buttons for plan selection, preferences, and source management.
* **Tkinter GUI**: Optional desktop interface to manually trigger each agent.

### Default News Sources

The system comes preloaded with a pool of well known, high-impact news outlets:

* BBC
* CNN
* Reuters
* NYTimes
* The Guardian
* Al Jazeera
* Associated Press
* Washington Post
* Wall Street Journal
* The Economist

## Quick Start (Local)

### 1. Clone & Configure

```bash
git clone https://github.com/your-username/auto_journalist.git
cd auto_journalist
cp .env.template .env
```

Edit `.env` to include at minimum:

```ini
DATABASE_URL=postgresql://user:password@localhost:5432/auto_journalist
OPENAI_API_KEY=sk-your_openai_key
TELEGRAM_TOKEN=123456789:ABCDEF...
OUTPUT_DIR=output
PUBLIC_DIR=public
# Optional: add extra RSS sources
EXTRA_SOURCES="Reuters|http://feeds.reuters.com/reuters/topNews|False"
```

### 2. Install Dependencies

Using Poetry (recommended):

```bash
poetry install
poetry shell
```

Or using venv + pip:

```bash
python3.11 -m venv .venv
source .venv/bin/activate     # macOS/Linux
pip install --upgrade pip
pip install .
```

### 3. Initialize Database

Make sure PostgreSQL is running and create the database:

```bash
psql -U user -c "CREATE DATABASE auto_journalist;"
alembic upgrade head
```

This will create tables: `users`, `preferences`, `sources`, `user_sources`, `articles`, `summaries`, `factchecks`, `commentaries`, `issues`.

### 4. Run the Telegram Bot

Start the bot so users can register and set preferences:

```bash
python -m auto_journalist.main run_bot
```

In Telegram, send `/start` to your bot, then `/plan premium` (if you want custom sources), `/set technology daily`, etc.

### 5. Execute the News Pipeline

In another terminal, run the full daily pipeline:

```bash
python -m auto_journalist.main run_daily
```

To generate charts summarizing article counts and fact-check results, run:

```bash
python -m auto_journalist.main run_analytics
```

This will:

1. Crawl RSS & social feeds.
2. Summarize new articles via OpenAI.
3. Fact-check summaries via Wikipedia.
4. Generate contextual commentary via OpenAI.
5. Format and archive a Markdown/HTML newsletter in `output/` and `public/rss/`.
6. Send personalized messages to Telegram users based on their topics and frequency.

### 6. Launch the Simple GUI

Start the Tkinter-based interface to manually trigger agents or view analytics:

```bash
python -m auto_journalist.gui
```

The GUI exposes an **Analytics** button to display the generated charts.

### 7. Stream News to a Channel

To stream every verified article to a Telegram channel as soon as it's processed, run:

```bash
python -m auto_journalist.main run_stream
```


### 8. Automate Daily Runs

#### A) Using Cron

Add to your crontab (`crontab -e`):

```cron
0 6 * * * cd /path/to/auto_journalist && /path/to/.venv/bin/python -m auto_journalist.main run_daily >> daily.log 2>&1
```

#### B) Using APScheduler (optional)

Modify `main.py` to include a `daemon` command that schedules `run_daily` at 06:00 each morning.

## Quick Start (Docker)

1. Copy `.env` and fill in keys as above.

2. Build and start containers:

```bash
docker-compose up --build -d
```

3. Run the bot inside Docker:

```bash
docker-compose run --rm app python -m auto_journalist.main run_bot
```

4. To trigger the pipeline manually in Docker:

```bash
docker-compose run --rm app python -m auto_journalist.main run_daily
```

5. (Host cron) Schedule inside the host system:

```cron
0 6 * * * cd /path/to/auto_journalist && docker-compose run --rm app python -m auto_journalist.main run_daily
```

## Bot Command Reference

* `/start` — Register with the bot.
* `/plan <basic|premium>` — Choose your user plan.
* `/set <topic> <frequency>` — Set news topic and frequency (hourly, daily, weekly).
* `/addsource <name> <url>` — (Premium only) Add a custom RSS/social source.
* `/removesource <url>` — (Premium only) Remove a custom source.
* `/listsources` — List default and your custom sources.
* `/verify <url|text>` — Fact-check a news link or snippet.

### What is a Source URL?

A source URL is the address of an RSS feed or social feed that the crawler reads. Examples include RSS feeds from major news websites or subreddit feeds such as:

```
https://rss.cnn.com/rss/edition.rss
https://rss.nytimes.com/services/xml/rss/nyt/World.xml
https://www.reddit.com/r/technology/.rss
```
Use `/addsource <name> <url>` to add any feed you like.
* `/help` — Show this help message.

## Directory Structure

```
auto_journalist/
├── __init__.py
├── config.py          # Environment variables & defaults
├── db.py              # Async SQLAlchemy engine & session
├── models.py          # ORM models: users, preferences, sources, articles, summaries, etc.
├── agents/            # Agent classes for each pipeline step
│   ├── base_agent.py
│   ├── crawler_agent.py
│   ├── source_manager_agent.py
│   ├── summarizer_agent.py
│   ├── factcheck_agent.py
│   ├── commentary_agent.py
│   ├── formatter_agent.py
│   ├── publisher_agent.py
│   ├── bot_agent.py
│   └── orchestrator_agent.py
├── templates/         # Jinja2 templates for newsletters
│   ├── newsletter.md.j2
│   └── newsletter.html.j2
├── main.py            # CLI entrypoint (`run_daily`, `run_bot`)
├── publish.py         # Manual publish command (alias for run_daily)
├── migrations/        # Alembic migrations for DB schema
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py
├── Dockerfile         # Multi-stage build for Docker image
├── docker-compose.yml # Orchestrates Postgres and app
└── README.md          # This file
```

## Testing & Development

* **Run tests** with `pytest` (coverage >95%).
* **Lint/format** with `black`, `ruff`, and `mypy`.
* Use **SQLTools** in VS Code or `psql` CLI to inspect tables.
* Use **Docker Remote – Containers** to develop in a matching environment.

## Extensibility

* Add or remove default sources in `config.DEFAULT_SOURCES`.
* Enhance `FactCheckAgent` to use other APIs (PolitiFact, Snopes).
* Customize Jinja2 templates in `templates/`.
* Add new channels (email, Slack) by creating a new Publisher agent.

---

Generated by the Auto-Journalist scaffolding process.
