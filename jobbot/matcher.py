from __future__ import annotations
import re
from .models import Job

def _experience_overlaps(text: str, minimum: float, maximum: float) -> bool:
    """Accept missing/unparseable experience; reject clear ranges outside the target band."""
    values = [float(v) for v in re.findall(r"\d+(?:\.\d+)?", text)]
    if not values:
        return True
    low, high = (values[0], values[1]) if len(values) > 1 else (values[0], values[0])
    return high >= minimum and low <= maximum

def score(job: Job, matching: dict, minimum_experience: float = 0, maximum_experience: float = 99) -> Job:
    title = job.title.lower()
    text = " ".join([title, job.company, job.location, job.experience, job.skills]).lower()
    excludes = [word.lower() for word in matching["exclude_keywords"]]
    hits = [word for word in excludes if word in text]
    if hits:
        job.skip_reason = "Excluded: " + ", ".join(hits)
        return job
    if not any(word.lower() in title for word in matching["required_primary_title_keywords"]):
        job.skip_reason = "Primary .NET/ASP.NET skill not present in job title"
        return job
    if not _experience_overlaps(job.experience, minimum_experience, maximum_experience):
        job.skip_reason = f"Experience outside {minimum_experience}-{maximum_experience} years"
        return job
    role_hits = sum(word.lower() in title for word in matching["target_title_keywords"])
    stack_hits = sum(word.lower() in text for word in matching["resume_stack_keywords"])
    location_hits = sum(word.lower() in text for word in matching["preferred_locations"])
    # Title carries the most weight; generic C#/frontend roles cannot qualify on location alone.
    # A direct .NET title is a required, high-confidence résumé signal.
    job.score = min(role_hits, 1) * 40 + 15 + min(stack_hits, 4) * 10
    job.score += min(location_hits, 1) * 10
    job.score += 10 if _experience_overlaps(job.experience, minimum_experience, maximum_experience) else 0
    return job
