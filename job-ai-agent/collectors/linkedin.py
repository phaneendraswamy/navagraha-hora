import logging
from typing import Any
from urllib.parse import urlencode

from backend.schemas import RawJobCreate
from collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class LinkedInCollector(BaseCollector):
    source = "linkedin"

    async def collect(self, query: str, location: str, max_pages: int = 1, **_: Any) -> list[RawJobCreate]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright is not installed. Run `playwright install chromium` after installing requirements.")
            return []

        safe_pages = max(1, min(max_pages, self.settings.collector_max_pages))
        collected: list[RawJobCreate] = []

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.settings.linkedin_headless)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 768},
            )
            page = await context.new_page()

            for page_number in range(safe_pages):
                params = urlencode(
                    {
                        "keywords": query,
                        "location": location,
                        "start": page_number * 25,
                    }
                )
                url = f"https://www.linkedin.com/jobs/search/?{params}"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await self.human_delay()
                    collected.extend(await self._extract_cards(page))
                except Exception as exc:  # Playwright surfaces several transport-specific exceptions.
                    logger.warning("LinkedIn collection stopped on page %s: %s", page_number + 1, exc)
                    break

            await context.close()
            await browser.close()

        return self._dedupe(collected)

    async def _extract_cards(self, page: Any) -> list[RawJobCreate]:
        cards = await page.locator("ul.jobs-search__results-list li, div.base-card").all()
        raw_jobs: list[RawJobCreate] = []

        for card in cards[:25]:
            title = await self._text(card, "h3")
            company = await self._text(card, "h4, .base-search-card__subtitle")
            location = await self._text(card, ".job-search-card__location")
            posted_date = await self._text(card, "time")
            link = await self._attribute(card, "a", "href")
            if not title or not company:
                continue

            payload = {
                "job_id": self._job_id_from_url(link),
                "title": title,
                "company": company,
                "location": location,
                "posted_date": posted_date,
                "url": link,
                "summary": f"{title} at {company}. Location: {location}.",
            }
            raw_jobs.append(
                RawJobCreate(
                    source=self.source,
                    source_job_id=payload["job_id"],
                    url=link,
                    payload=payload,
                )
            )
        return raw_jobs

    async def _text(self, locator: Any, selector: str) -> str:
        try:
            child = locator.locator(selector).first
            if await child.count() == 0:
                return ""
            return " ".join((await child.inner_text()).split())
        except Exception:
            return ""

    async def _attribute(self, locator: Any, selector: str, attribute: str) -> str:
        try:
            child = locator.locator(selector).first
            if await child.count() == 0:
                return ""
            return (await child.get_attribute(attribute)) or ""
        except Exception:
            return ""

    def _dedupe(self, jobs: list[RawJobCreate]) -> list[RawJobCreate]:
        seen: set[str] = set()
        deduped: list[RawJobCreate] = []
        for job in jobs:
            key = job.source_job_id or job.url or repr(job.payload)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(job)
        return deduped

    @staticmethod
    def _job_id_from_url(url: str) -> str:
        if not url:
            return ""
        cleaned = url.split("?")[0].rstrip("/")
        return cleaned.rsplit("/", 1)[-1]

