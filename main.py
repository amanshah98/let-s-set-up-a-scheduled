from __future__ import annotations
import argparse, asyncio, webbrowser
from pathlib import Path
from jobbot.autofill import fill_application, open_application_form, pause_before_submit, submit_final_application
from jobbot.browser import persistent_context, wait_for_manual_login
from jobbot.config import load
from jobbot.matcher import score
from jobbot.review import render
from jobbot.scrapers import IndeedScraper, LinkedInScraper, NaukriScraper
from jobbot.tracker import Tracker

SOURCES = {"naukri": NaukriScraper, "linkedin": LinkedInScraper, "indeed": IndeedScraper}

async def run_search(config: dict, source: str) -> None:
    scraper_type = SOURCES[source]
    pw, context = await persistent_context(config, source)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        scraper = scraper_type(page, config)
        await wait_for_manual_login(page, scraper.login_url, source.title())
        tracker = Tracker(config["runtime"]["database_path"])
        new = 0
        for job in await scraper.search(config["search"]["keywords"]):
            job = score(job, config["matching"], config["search"]["min_experience_years"], config["search"]["max_experience_years"])
            new += tracker.upsert_shortlist(job)
        output = render(tracker.jobs(None, source), config["runtime"]["shortlist_html_path"])
        print(f"Saved {new} new records. Open {output.resolve()} to review.")
        webbrowser.open(output.resolve().as_uri())
    finally:
        await context.close(); await pw.stop()

async def run_autofill(config: dict, url: str) -> None:
    tracker = Tracker(config["runtime"]["database_path"])
    record = next((row for row in tracker.jobs("approved") if row["url"] == url), None)
    if not record:
        raise SystemExit("That job is not approved. Review it first, then run approve <job-url>.")
    source = record["source"]
    pw, context = await persistent_context(config, source)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        input("Open the site's application form yourself (and resolve any CAPTCHA), then press Enter here to fill safe fields... ")
        filled, manual = await fill_application(page, config["profile"], config["field_mapping"])
        notes = "Filled: " + ", ".join(filled or ["nothing"]) + ". Manual: " + "; ".join(manual or ["none"])
        print(notes)
        if await pause_before_submit(page, record["title"]):
            tracker.set_status(url, "applied", notes)
            print("Logged as applied (based on your manual confirmation).")
        else:
            tracker.set_status(url, "approved", notes)
            print("Left approved/pending final submission.")
    finally:
        await context.close(); await pw.stop()

async def run_autoapply(config: dict, source: str) -> None:
    if not config["auto_apply"]["enabled"]:
        raise SystemExit("Auto-apply is disabled in config.yaml.")
    scraper_type = SOURCES[source]
    pw, context = await persistent_context(config, source)
    tracker = Tracker(config["runtime"]["database_path"])
    minimum = config["auto_apply"]["minimum_match_percent"]
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        scraper = scraper_type(page, config)
        await wait_for_manual_login(page, scraper.login_url, source.title())
        for job in await scraper.search(config["search"]["keywords"]):
            job = score(job, config["matching"], config["search"]["min_experience_years"], config["search"]["max_experience_years"])
            tracker.upsert_shortlist(job)
        candidates = [row for row in tracker.jobs("pending", source) if row["score"] >= minimum]
        for record in candidates:
            await page.goto(record["url"], wait_until="domcontentloaded")
            opened, open_note = await open_application_form(page)
            if not opened:
                tracker.set_status(record["url"], "pending", open_note)
                continue
            filled, manual = await fill_application(page, config["profile"], config["field_mapping"])
            if any("blank in config.yaml" in item or "path does not exist" in item for item in manual):
                tracker.set_status(record["url"], "pending", "Blocked: " + "; ".join(manual))
                continue
            submitted, note = await submit_final_application(page)
            tracker.set_status(record["url"], "applied" if submitted else "pending", f"{open_note}. Filled: {', '.join(filled)}. {note}")
            await page.wait_for_timeout(config["runtime"]["search_delay_seconds"] * 1000)
        output = render(tracker.jobs(None, source), config["runtime"]["shortlist_html_path"])
        print(f"Updated report: {output.resolve()}")
    finally:
        await context.close(); await pw.stop()

def main() -> None:
    parser = argparse.ArgumentParser(description="Local human-in-the-loop job helper")
    parser.add_argument("command", choices=["search", "autoapply", "approve", "skip", "autofill", "review", "status"])
    parser.add_argument("value", nargs="?", help="source for search, or the exact job URL")
    args = parser.parse_args()
    config = load()
    tracker = Tracker(config["runtime"]["database_path"])
    if args.command == "search":
        source = args.value or "naukri"
        if source == "all":
            for site in SOURCES:
                asyncio.run(run_search(config, site))
        elif source in SOURCES:
            asyncio.run(run_search(config, source))
        else:
            raise SystemExit("Choose naukri, linkedin, indeed, or all.")
    elif args.command == "autoapply":
        source = args.value or "naukri"
        if source == "all":
            for site in SOURCES:
                asyncio.run(run_autoapply(config, site))
        elif source in SOURCES:
            asyncio.run(run_autoapply(config, source))
        else:
            raise SystemExit("Choose naukri, linkedin, indeed, or all.")
    elif args.command == "review":
        path = render(tracker.jobs(None), config["runtime"]["shortlist_html_path"])
        webbrowser.open(path.resolve().as_uri()); print(path.resolve())
    elif args.command == "status":
        for status in ("pending", "approved", "applied", "skipped"):
            print(f"{status}: {len(tracker.jobs(status))}")
    else:
        if not args.value: raise SystemExit("This command needs the exact job URL.")
        if args.command == "approve": tracker.set_status(args.value, "approved"); print("Approved. Run: python main.py autofill <job-url>")
        elif args.command == "skip": tracker.set_status(args.value, "skipped"); print("Skipped.")
        else: asyncio.run(run_autofill(config, args.value))

if __name__ == "__main__": main()
