import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import markdown_it
import sqlalchemy as sa

from ..db import get_session
from ..models import Summary, FactCheck, Commentary, Issue

class FormatterAgent:
    def __init__(self):
        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(searchpath=str(templates_dir))
        )
        self.md = markdown_it.MarkdownIt()

    async def run(self):
        async for session in get_session():
            today = datetime.utcnow().date()
            exists = await session.execute(
                sa.select(Issue).where(sa.func.date(Issue.date) == today)
            )
            if exists.scalar_one_or_none():
                return

            stmt = (
                sa.select(Summary, FactCheck, Commentary)
                .join(FactCheck, FactCheck.summary_id == Summary.id)
                .join(Commentary, Commentary.summary_id == Summary.id)
                .where(sa.func.date(Summary.created_at) == today)
            )
            rows = (await session.execute(stmt)).all()

            context = []
            for summary, factcheck, commentary in rows:
                context.append({
                    "summary": summary,
                    "fact": factcheck,
                    "commentary": commentary,
                })

            template_md = self.env.get_template("newsletter.md.j2")
            markdown_content = template_md.render(items=context, date=today)

            template_html = self.env.get_template("newsletter.html.j2")
            html_content = template_html.render(
                body=self.md.render(markdown_content),
                date=today
            )

            os.makedirs("output", exist_ok=True)
            os.makedirs("public/rss", exist_ok=True)
            fname_base = f"newsletter_{today}"
            txt_path = os.path.join("output", f"{fname_base}.txt")
            html_path = os.path.join("output", f"{fname_base}.html")
            with open(txt_path, "w") as f_txt:
                f_txt.write(markdown_content)
            with open(html_path, "w") as f_html:
                f_html.write(html_content)

            rss_path = os.path.join("public/rss", f"{today}.html")
            with open(rss_path, "w") as f_rss:
                f_rss.write(html_content)

            issue = Issue(
                date=today,
                filename_html=html_path,
                filename_txt=txt_path,
                created_at=datetime.utcnow()
            )
            session.add(issue)
            await session.commit()