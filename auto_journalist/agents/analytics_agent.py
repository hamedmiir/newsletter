import os
import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
import sqlalchemy as sa

from .base_agent import BaseAgent
from ..db import get_session
from ..models import Article, Summary, FactCheck, FactStatusEnum


class AnalyticsAgent(BaseAgent):
    """Generate analytics charts from stored articles and fact checks."""

    async def run(self) -> None:
        async for session in get_session():
            # Article count per source
            result = await session.execute(
                sa.select(Article.source, sa.func.count(Article.id)).group_by(Article.source)
            )
            article_counts = dict(result.all())

            # Fact check status counts per source
            result = await session.execute(
                sa.select(
                    Article.source,
                    FactCheck.status,
                    sa.func.count(FactCheck.id),
                )
                .join(Summary, Summary.article_id == Article.id)
                .join(FactCheck, FactCheck.summary_id == Summary.id)
                .group_by(Article.source, FactCheck.status)
            )

            fact_data = {}
            for source, status, count in result.all():
                fact_data.setdefault(source, {})[status.value] = count

            # Prepare output directory
            os.makedirs("output", exist_ok=True)

            # Chart: articles per source
            sources = list(article_counts.keys())
            counts = [article_counts[s] for s in sources]
            plt.figure(figsize=(6, 4))
            plt.bar(sources, counts)
            plt.title("Articles per Source")
            plt.xlabel("Source")
            plt.ylabel("Articles")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            articles_png = os.path.join("output", "articles_per_source.png")
            plt.savefig(articles_png)
            plt.close()

            # Chart: fact check distribution
            statuses = [s.value for s in FactStatusEnum]
            data = {s: [] for s in statuses}
            for src in sources:
                dist = fact_data.get(src, {})
                for status in statuses:
                    data[status].append(dist.get(status, 0))

            plt.figure(figsize=(6, 4))
            bottom = [0] * len(sources)
            for status in statuses:
                plt.bar(sources, data[status], bottom=bottom, label=status)
                bottom = [bottom[i] + data[status][i] for i in range(len(sources))]
            plt.title("Fact Check Status")
            plt.xlabel("Source")
            plt.ylabel("Count")
            plt.xticks(rotation=45, ha="right")
            plt.legend()
            plt.tight_layout()
            fact_png = os.path.join("output", "factchecks_per_source.png")
            plt.savefig(fact_png)
            plt.close()

            self.logger.info("Saved analytics charts: %s, %s", articles_png, fact_png)

