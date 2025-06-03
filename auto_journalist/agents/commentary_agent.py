import sqlalchemy as sa
from sqlalchemy import select
from ..db import get_session
from ..models import Summary, FactCheck, Commentary
from .base_agent import BaseAgent

class CommentaryAgent(BaseAgent):
    def __init__(self, model_name="gpt-4o"):
        super().__init__()
        self.model = model_name

    async def generate_commentary(self, summary_text, fact_status, summary_id):
        prompt = [
            {"role": "system", "content": "You are a contextual commentary engine."},
            {
                "role": "user",
                "content": (
                    "Provide a single-paragraph contextual analysis in a neutral yet engaging tone. "
                    "Mention historical parallels, market impact, or societal angles as relevant.\n\n"
                    f"Summary: {summary_text}\nFact-check status: {fact_status.value}"
                ),
            },
        ]
        response = await self.call_openai(
            model=self.model,
            messages=prompt,
            max_tokens=200
        )
        if response is None:
            self.logger.error(f"Skipping commentary for summary_id={summary_id} due to OpenAI failure.")
            return None
        return response.choices[0].message.content

    async def run(self):
        async for session in get_session():
            stmt = (
                select(Summary, FactCheck)
                .join(FactCheck, FactCheck.summary_id == Summary.id)
                .outerjoin(Commentary, Commentary.summary_id == Summary.id)
                .where(Commentary.id.is_(None))
            )
            result = await session.execute(stmt)
            rows = result.all()

            for summary, factcheck in rows:
                commentary_text = await self.generate_commentary(
                    summary.summary_text, factcheck.status, summary.id
                )
                if commentary_text is None:
                    continue
                commentary = Commentary(
                    summary_id=summary.id,
                    commentary_text=commentary_text
                )
                session.add(commentary)

            await session.commit()