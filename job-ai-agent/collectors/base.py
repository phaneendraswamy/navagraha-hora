import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any

from backend.core.config import get_settings
from backend.schemas import RawJobCreate


class CollectorError(RuntimeError):
    pass


class BaseCollector(ABC):
    source: str

    def __init__(self) -> None:
        self.settings = get_settings()

    @abstractmethod
    async def collect(self, **kwargs: Any) -> list[RawJobCreate]:
        raise NotImplementedError

    async def human_delay(self) -> None:
        await asyncio.sleep(
            random.uniform(
                self.settings.collector_min_delay_seconds,
                self.settings.collector_max_delay_seconds,
            )
        )

