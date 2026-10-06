from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(slots=True)
class Job:
    source: str
    title: str
    company: str
    location: str = ""
    experience: str = ""
    skills: str = ""
    url: str = ""
    posted_date: str = ""
    score: int = 0
    skip_reason: str = ""

    def record(self) -> dict[str, object]:
        return asdict(self)
