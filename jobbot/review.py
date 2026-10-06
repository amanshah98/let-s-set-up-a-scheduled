from __future__ import annotations
from datetime import date
from html import escape
from pathlib import Path
from sqlite3 import Row

def render(rows: list[Row], output_path: str) -> Path:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    counts = {status: sum(r["status"] == status for r in rows) for status in ("pending", "approved", "applied", "skipped")}
    cards = "\n".join(f'''<tr><td>{escape(str(r["status"]))}</td><td>{escape(str(r["source"]))}</td><td><a href="{escape(str(r["url"]))}" target="_blank">{escape(str(r["title"]))}</a></td><td>{escape(str(r["company"] or ""))}</td><td>{escape(str(r["location"] or ""))}</td><td>{r["score"]}%</td><td>{escape(str(r["experience"] or ""))}</td><td>{escape(str(r["skip_reason"] or ""))}</td></tr>''' for r in rows)
    html = f'''<!doctype html><html><head><meta charset="utf-8"><title>Job report</title><style>body{{font:15px system-ui;margin:2rem;color:#172033}} table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d8dee9;padding:.65rem;text-align:left}}th{{background:#eef3f9}}a{{color:#0757a6}}code{{background:#f2f4f7;padding:.2rem}}.stats{{display:flex;gap:1rem}}.stat{{background:#eef3f9;padding:.8rem 1rem;border-radius:.4rem}}</style></head><body><h1>All jobs found - {date.today().isoformat()}</h1><div class="stats"><div class="stat"><b>{len(rows)}</b> unique jobs found</div><div class="stat"><b>{counts["applied"]}</b> automatically applied</div><div class="stat"><b>{counts["pending"]}</b> pending</div><div class="stat"><b>{counts["skipped"]}</b> skipped</div></div><p>Fit score is out of 100. Auto-apply considers only 75%+ matches. Review links, then approve selected jobs with <code>python main.py approve &lt;job-url&gt;</code>.</p><table><thead><tr><th>Status</th><th>Site</th><th>Role</th><th>Company</th><th>Location</th><th>Fit</th><th>Experience</th><th>Skip reason</th></tr></thead><tbody>{cards}</tbody></table></body></html>'''
    Path(output_path).write_text(html, encoding="utf-8")
    return Path(output_path)
