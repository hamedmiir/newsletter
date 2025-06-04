import asyncio
import threading
import tkinter as tk
import os
from tkinter.scrolledtext import ScrolledText

from .agents.orchestrator_agent import OrchestratorAgent
from .agents.crawler_agent import CrawlerAgent
from .agents.summarizer_agent import SummarizerAgent
from .agents.factcheck_agent import FactCheckAgent
from .agents.commentary_agent import CommentaryAgent
from .agents.formatter_agent import FormatterAgent
from .agents.publisher_agent import PublisherAgent
from .agents.analytics_agent import AnalyticsAgent


class AgentGUI:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        master.title("Auto-Journalist Manager")

        # Log area
        self.text = ScrolledText(master, width=80, height=20)
        self.text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        frame = tk.Frame(master)
        frame.pack(fill=tk.X)
        tk.Button(frame, text="Run Daily", command=self.run_daily).pack(side=tk.LEFT)
        tk.Button(frame, text="Crawler", command=self.run_crawler).pack(side=tk.LEFT)
        tk.Button(frame, text="Summarizer", command=self.run_summarizer).pack(
            side=tk.LEFT
        )
        tk.Button(frame, text="Fact Check", command=self.run_factcheck).pack(
            side=tk.LEFT
        )
        tk.Button(frame, text="Commentary", command=self.run_commentary).pack(
            side=tk.LEFT
        )
        tk.Button(frame, text="Formatter", command=self.run_formatter).pack(
            side=tk.LEFT
        )
        tk.Button(frame, text="Publish", command=self.run_publisher).pack(side=tk.LEFT)
        tk.Button(frame, text="Analytics", command=self.run_analytics).pack(side=tk.LEFT)

    def log(self, message: str) -> None:
        self.text.insert(tk.END, message + "\n")
        self.text.see(tk.END)

    def run_async(self, coro):
        def task():
            self.log(f"Starting {coro.__qualname__}()...")
            try:
                asyncio.run(coro())
                self.log("Done.")
            except Exception as e:  # pragma: no cover - simple GUI diagnostic
                self.log(f"Error: {e}")

        threading.Thread(target=task, daemon=True).start()

    # Button callbacks
    def run_daily(self):
        orchestrator = OrchestratorAgent()
        self.run_async(orchestrator.run_daily)

    def run_crawler(self):
        agent = CrawlerAgent()
        self.run_async(agent.run)

    def run_summarizer(self):
        agent = SummarizerAgent()
        self.run_async(agent.run)

    def run_factcheck(self):
        agent = FactCheckAgent()
        self.run_async(agent.run)

    def run_commentary(self):
        agent = CommentaryAgent()
        self.run_async(agent.run)

    def run_formatter(self):
        agent = FormatterAgent()
        self.run_async(agent.run)

    def run_publisher(self):
        agent = PublisherAgent()
        self.run_async(agent.run)

    def run_analytics(self):
        agent = AnalyticsAgent()

        def task():
            self.log("Starting AnalyticsAgent.run()...")
            try:
                import asyncio
                asyncio.run(agent.run())
                self.log("Analytics generated in output/ directory.")
                self.show_analytics()
            except Exception as e:  # pragma: no cover - GUI diagnostic
                self.log(f"Error: {e}")

        threading.Thread(target=task, daemon=True).start()

    def show_analytics(self):
        try:
            from PIL import Image, ImageTk
        except Exception:
            self.log("Pillow is required to display analytics charts.")
            return

        window = tk.Toplevel(self.master)
        window.title("Analytics Dashboard")

        for img_name in ["articles_per_source.png", "factchecks_per_source.png"]:
            path = os.path.join("output", img_name)
            if not os.path.exists(path):
                continue
            img = Image.open(path)
            photo = ImageTk.PhotoImage(img)
            label = tk.Label(window, image=photo)
            label.image = photo
            label.pack()


def main() -> None:
    root = tk.Tk()
    AgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
