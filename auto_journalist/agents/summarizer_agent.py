import sqlalchemy as sa
from sqlalchemy import select
from ..db import get_session
from ..models import Article, Summary
from .base_agent import BaseAgent

class SummarizerAgent(BaseAgent):
    def __init__(self, model_name="gpt-4o"):
        super().__init__()
        self.model = model_name

    async def summarize_article(self, article_json, article_id):
        prompt = [
            {"role": "system", "content": "You are a summarization engine."},
            {
                "role": "user",
                "content": (
                    "Summarize the following article in no more than 120 words as bullet points. "
                    "Include source, author, publish date, and a topic tag.\n\n"
                    f"Article data: {article_json}"
                ),
            },
        ]
        response = await self.call_openai(
            model=self.model,
            messages=prompt,
            max_tokens=300
        )
        if response is None:
            self.logger.error(f"Skipping summary for article_id={article_id} due to OpenAI failure.")
            return None
        return response.choices[0].message.content

    async def run(self):
        async for session in get_session():
            # Select all articles with no corresponding Summary
            stmt = (
                select(Article)
                .outerjoin(Summary, Summary.article_id == Article.id)
                .where(Summary.id.is_(None))
            )
            result = await session.execute(stmt)
            articles = result.scalars().all()

            for article in articles:
                summary_text = await self.summarize_article(article.raw_json, article.id)
                if summary_text is None:
                    continue  # skip if OpenAI failed
                summary = Summary(
                    article_id=article.id,
                    summary_text=summary_text
                )
                session.add(summary)

            await session.commit()
