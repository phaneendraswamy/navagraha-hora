import logging
from typing import Any

import httpx

from backend.schemas import RawJobCreate
from collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class GreenhouseCollector(BaseCollector):
    source = "greenhouse"

    async def collect(self, boards: list[str], **_: Any) -> list[RawJobCreate]:
        raw_jobs: list[RawJobCreate] = []
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for board in boards:
                board_token = board.strip()
                if not board_token:
                    continue
                raw_jobs.extend(await self._collect_board(client, board_token))
                await self.human_delay()
        return raw_jobs

    async def _collect_board(self, client: httpx.AsyncClient, board_token: str) -> list[RawJobCreate]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Greenhouse board collection failed for %s: %s", board_token, exc)
            return []

        data = response.json()
        jobs = data.get("jobs") or []
        raw_jobs = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            job["board_token"] = board_token
            job["company"] = data.get("name") or board_token
            raw_jobs.append(
                RawJobCreate(
                    source=self.source,
                    source_job_id=str(job.get("id") or ""),
                    url=job.get("absolute_url"),
                    payload=job,
                )
            )
        return raw_jobs

