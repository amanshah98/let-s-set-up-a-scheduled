from __future__ import annotations
from urllib.parse import quote_plus
from .base import Scraper
from ..models import Job

class LinkedInScraper(Scraper):
    """Same normalized output as Naukri; enable only after validating selectors in your account."""
    source = "linkedin"
    login_url = "https://www.linkedin.com/login"

    def __init__(self, page, config: dict): self.page, self.config = page, config
    async def search(self, keywords: list[str]) -> list[Job]:
        jobs: list[Job] = []
        for keyword in keywords:
            for location in self.config["search"]["locations"]:
                await self.page.goto(f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location={quote_plus(location)}", wait_until="domcontentloaded")
                cards = self.page.locator(".job-card-container, li.jobs-search-results__list-item")
                for i in range(min(await cards.count(), self.config["search"]["max_results_per_keyword"])):
                    card = cards.nth(i)
                    async def get(selector: str) -> str:
                        locator = card.locator(selector).first
                        return (await locator.inner_text()).strip() if await locator.count() else ""
                    link = card.locator("a.job-card-container__link, a.base-card__full-link").first
                    jobs.append(Job(self.source, await get(".job-card-list__title, .base-search-card__title"), await get(".job-card-container__company-name, .base-search-card__subtitle"), await get(".job-card-container__metadata-item, .job-search-card__location"), url=(await link.get_attribute("href") if await link.count() else "")))
                await self.page.wait_for_timeout(self.config["runtime"]["search_delay_seconds"] * 1000)
        return jobs
