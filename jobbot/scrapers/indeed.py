from __future__ import annotations
from urllib.parse import quote_plus
from .base import Scraper
from ..models import Job

class IndeedScraper(Scraper):
    """Indeed India search adapter; selectors stay isolated here for easy updates."""
    source = "indeed"
    login_url = "https://in.indeed.com/account/login"

    def __init__(self, page, config: dict):
        self.page, self.config = page, config

    async def search(self, keywords: list[str]) -> list[Job]:
        jobs: list[Job] = []
        limit = self.config["search"]["max_results_per_keyword"]
        for keyword in keywords:
            for location in self.config["search"]["locations"]:
                url = f"https://in.indeed.com/jobs?q={quote_plus(keyword)}&l={quote_plus(location)}"
                await self.page.goto(url, wait_until="domcontentloaded")
                cards = self.page.locator("div.job_seen_beacon, .jobsearch-ResultsList > li")
                for index in range(min(await cards.count(), limit)):
                    card = cards.nth(index)
                    async def get(selector: str) -> str:
                        node = card.locator(selector).first
                        return (await node.inner_text()).strip() if await node.count() else ""
                    link = card.locator("h2.jobTitle a, a[data-jk]").first
                    href = await link.get_attribute("href") if await link.count() else ""
                    if href and href.startswith("/"):
                        href = "https://in.indeed.com" + href
                    jobs.append(Job(
                        source=self.source,
                        title=await get("h2.jobTitle, .jobTitle"),
                        company=await get("[data-testid='company-name'], .companyName"),
                        location=await get("[data-testid='text-location'], .companyLocation"),
                        # Card text is retained as a fallback when skills are not exposed separately.
                        skills=await card.inner_text(),
                        posted_date=await get(".date, [data-testid='myJobsStateDate']"),
                        url=href or "",
                    ))
                await self.page.wait_for_timeout(self.config["runtime"]["search_delay_seconds"] * 1000)
        return jobs
