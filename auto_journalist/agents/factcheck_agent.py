from sqlalchemy import select
from ..db import get_session
from ..models import Summary, FactCheck, FactStatusEnum
from .base_agent import BaseAgent

class FactCheckAgent(BaseAgent):
    def __init__(self, model_name="gpt-4o"):
        super().__init__()
        self.model = model_name

    async def fact_check(self, summary_text, summary_id=None):
        prompt = [
            {"role": "system", "content": "You are a fact-checking engine."},
            {
                "role": "user",
                "content": (
                    "Check the following text against reputable sources such as Wikipedia. "
                    "Respond with a JSON object containing:\n"
                    "{\"status\": \"verified\" | \"disputed\" | \"not_verifiable\", \"citations\": [...], \"analysis\": <short reason>}\n"
                    f"Text: {summary_text}"
                ),
            },
        ]
        response = await self.call_openai(
            model=self.model,
            messages=prompt,
            max_tokens=200
        )
        if response is None:
            if summary_id is not None:
                self.logger.error(
                    f"Marking FactCheck(summary_id={summary_id}) as NOT_VERIFIABLE due to OpenAI failure."
                )
            else:
                self.logger.error("Fact check failed due to OpenAI failure.")
            return FactStatusEnum.NOT_VERIFIABLE, [], ""

        try:
            import json
            payload = response.choices[0].message.content.strip()
            data = json.loads(payload)
            status_str = data.get("status", "not_verifiable")
            citations = data.get("citations", [])
            analysis = data.get("analysis", "")
            status = FactStatusEnum(status_str)
            return status, citations, analysis
        except Exception as e:
            self.logger.error(
                f"Error parsing FactCheck response for summary_id={summary_id}: {e!r}"
            )
            return FactStatusEnum.NOT_VERIFIABLE, [], ""

    async def fact_check_text(self, text: str):
        """Fact-check arbitrary user provided text or article."""
        return await self.fact_check(text, None)

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
                status, citations, _ = await self.fact_check(summary.summary_text, summary.id)
                fact = FactCheck(
                    summary_id=summary.id,
                    status=status,
                    citations=citations
                )
                session.add(fact)

            await session.commit()

