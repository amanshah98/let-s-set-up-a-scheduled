from __future__ import annotations
from abc import ABC, abstractmethod
from ..models import Job

class Scraper(ABC):
    source: str
    @abstractmethod
    async def search(self, keywords: list[str]) -> list[Job]: ...
