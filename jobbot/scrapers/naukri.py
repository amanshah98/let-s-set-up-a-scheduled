from __future__ import annotations
import re
from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from .base import Scraper
from ..models import Job

class NaukriScraper(Scraper):
    source = "naukri"
    login_url = "https://www.naukri.com/nlogin/login"

    def __init__(self, page, config: dict):
        self.page, self.config = page, config

    @staticmethod
    def _slug(value: str) -> str:
        # Naukri's path URLs use "dot-net", not a literal leading ".".
        value = re.sub(r"(?i)\.net", " dot net", value)
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    async def _open_results(self, url: str) -> bool:
        """Naukri may redirect to its logged-in homepage just after manual login."""
        for attempt in range(2):
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                return True
            except PlaywrightError as exc:
                if attempt == 0:
                    print("Naukri redirected after login; retrying the search once...")
                    await self.page.wait_for_timeout(2_000)
                    continue
                print(f"Naukri search navigation failed: {exc}")
        return False

    async def search(self, keywords: list[str]) -> list[Job]:
        jobs: list[Job] = []
        limit = self.config["search"]["max_results_per_keyword"]
        locations = self.config["search"]["locations"]
        for keyword in keywords:
            for location in locations:
                # The normal Naukri public search page. Selectors are isolated here because sites change.
                url = f"https://www.naukri.com/{self._slug(keyword)}-jobs-in-{self._slug(location)}"
                if not await self._open_results(url):
                    continue
                try:
                    await self.page.locator("article.jobTuple, .srp-jobtuple-wrapper").first.wait_for(timeout=12_000)
                except PlaywrightTimeoutError:
                    print("Naukri results did not load. If a CAPTCHA/login wall is visible, resolve it manually, then rerun.")
                    continue
                cards = self.page.locator("article.jobTuple, .srp-jobtuple-wrapper")
                for index in range(min(await cards.count(), limit)):
                    card = cards.nth(index)
                    async def text(selector: str) -> str:
                        node = card.locator(selector).first
                        return (await node.inner_text()).strip() if await node.count() else ""
                    link = card.locator("a.title, a[href*='job-listings']").first
                    href = await link.get_attribute("href") if await link.count() else ""
                    if href and href.startswith("/"):
                        href = "https://www.naukri.com" + href
                    jobs.append(Job(
                        source=self.source, title=await text("a.title"), company=await text("a.comp-name"),
                        location=await text(".locWdth"), experience=await text(".expwdth"),
                        skills=await text(".tags-gt"), posted_date=await text(".job-post-day"), url=href or ""
                    ))
                await self.page.wait_for_timeout(self.config["runtime"]["search_delay_seconds"] * 1000)
        return jobs
