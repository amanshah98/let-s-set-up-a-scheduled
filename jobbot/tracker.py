from __future__ import annotations
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from .models import Job

class Tracker:
    def __init__(self, database_path: str):
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(database_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
          url TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT NOT NULL, company TEXT,
          location TEXT, experience TEXT, skills TEXT, posted_date TEXT, score INTEGER,
          skip_reason TEXT, status TEXT NOT NULL DEFAULT 'pending',
          shortlisted_at TEXT, approved_at TEXT, applied_at TEXT, autofill_notes TEXT
        )""")
        self.db.commit()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def seen(self, url: str) -> bool:
        return bool(url and self.db.execute("SELECT 1 FROM jobs WHERE url=?", (url,)).fetchone())

    def upsert_shortlist(self, job: Job) -> bool:
        if not job.url:
            return False
        if self.seen(job.url):
            # Refresh score/details on a rescan while preserving any applied decision.
            self.db.execute("""UPDATE jobs SET title=?, company=?, location=?, experience=?, skills=?,
              posted_date=?, score=?, skip_reason=?,
              status=CASE WHEN status IN ('applied', 'approved') THEN status
                          WHEN ? <> '' THEN 'skipped' ELSE 'pending' END
              WHERE url=?""",
              (job.title, job.company, job.location, job.experience, job.skills, job.posted_date,
               job.score, job.skip_reason, job.skip_reason, job.url))
            self.db.commit()
            return False
        self.db.execute("""INSERT INTO jobs
          (url, source, title, company, location, experience, skills, posted_date, score, skip_reason, status, shortlisted_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
          (job.url, job.source, job.title, job.company, job.location, job.experience,
           job.skills, job.posted_date, job.score, job.skip_reason,
           "skipped" if job.skip_reason else "pending", self.now()))
        self.db.commit()
        return True

    def jobs(self, status: str | None = "pending", source: str | None = None) -> list[sqlite3.Row]:
        clauses, values = [], []
        if status is not None:
            clauses.append("status=?")
            values.append(status)
        if source is not None:
            clauses.append("source=?")
            values.append(source)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return self.db.execute(f"SELECT * FROM jobs{where} ORDER BY shortlisted_at DESC, score DESC", values).fetchall()

    def set_status(self, url: str, status: str, notes: str = "") -> None:
        columns = {"approved": "approved_at", "applied": "applied_at"}
        timestamp_column = columns.get(status)
        if timestamp_column:
            self.db.execute(f"UPDATE jobs SET status=?, {timestamp_column}=?, autofill_notes=? WHERE url=?", (status, self.now(), notes, url))
        else:
            self.db.execute("UPDATE jobs SET status=?, autofill_notes=? WHERE url=?", (status, notes, url))
        self.db.commit()
