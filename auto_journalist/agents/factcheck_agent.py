import sqlalchemy as sa
from sqlalchemy import select
from ..db import get_session
from ..models import Summary, FactCheck, FactStatusEnum
from .base_agent import BaseAgent

class FactCheckAgent(BaseAgent):
    def __init__(self, model_name="gpt-4o"):
        super().__init__()
        self.model = model_name

    async def fact_check(self, summary_text, summary_id):
        prompt = [
            {"role": "system", "content": "You are a fact-checking engine."},
            {
                "role": "user",
                "content": (
                    "Check the following summary's key claims against reputable sources (e.g., Wikipedia). "
                    "Respond with a JSON object containing:\n"
                    "{\"status\": \"verified\" | \"disputed\" | \"not_verifiable\", \"citations\": [...]}\n"
                    f"Summary: {summary_text}"
                ),
            },
        ]
        response = await self.call_openai(
            model=self.model,
            messages=prompt,
            max_tokens=200
        )
        if response is None:
            self.logger.error(f"Marking FactCheck(summary_id={summary_id}) as NOT_VERIFIABLE due to OpenAI failure.")
            return FactStatusEnum.NOT_VERIFIABLE, []

        try:
            import json
            payload = response.choices[0].message.content.strip()
            data = json.loads(payload)
            status_str = data.get("status", "not_verifiable")
            citations = data.get("citations", [])
            status = FactStatusEnum(status_str)
            return status, citations
        except Exception as e:
            self.logger.error(f"Error parsing FactCheck response for summary_id={summary_id}: {e!r}")
            return FactStatusEnum.NOT_VERIFIABLE, []

    async def run(self):
        async for session in get_session():
            stmt = (
                select(Summary)
                .outerjoin(FactCheck, FactCheck.summary_id == Summary.id)
                .where(FactCheck.id.is_(None))
            )
            result = await session.execute(stmt)
            summaries = result.scalars().all()

            for summary in summaries:
                status, citations = await self.fact_check(summary.summary_text, summary.id)
                fact = FactCheck(
                    summary_id=summary.id,
                    status=status,
                    citations=citations
                )
                session.add(fact)

            await session.commit()