# Local Job Search Helper (human-in-the-loop)

A local Python + Playwright helper for searching Naukri first, ranking roles, reviewing them in a browser-friendly HTML shortlist, and filling application fields only after your explicit approval. It **never clicks a final Submit/Apply button**. You open the form and resolve login/CAPTCHA screens yourself, then it fills configured fields and pauses. An application is marked applied only if you type `applied` after clicking the final action yourself.

## What is included

- `jobbot/scrapers/naukri.py`: Naukri search adapter (the initial end-to-end path).
- `jobbot/scrapers/linkedin.py`: same job model and a starter LinkedIn adapter to validate after Naukri works with your account.
- `jobbot/matcher.py`: transparent keyword scoring and exclusions.
- `jobbot/review.py`: local daily HTML shortlist.
- `jobbot/autofill.py`: editable label-to-field filling, resume upload, and an explicit manual-submit pause.
- `jobbot/tracker.py`: local SQLite tracking/deduplication.
- `config.yaml`: the only normal file to edit for search preferences and profile fields.

## Setup (Windows / PowerShell)

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/). During installation, choose **Add Python to PATH**.
2. In this project folder, create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies and Chromium:

   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```

4. Open `config.yaml` and fill the blank `profile` values. The résumé path already points to the supplied PDF; change it if you move the file. Do not put a password in this file.

## First Naukri run

```powershell
python main.py search naukri
```

A visible Chromium window opens using `.browser-data/naukri/`. Log in manually, complete any CAPTCHA yourself, then return to the terminal and press Enter. Cookies/session state are stored in that local browser-profile folder, not in source code. If Naukri shows a login wall or CAPTCHA during search, resolve it in the visible browser and rerun rather than trying to automate around it.

Every unique result found is saved in `data/jobs.sqlite3`, and a local [daily job report](outputs/daily-shortlist.html) is opened. Its summary shows total jobs found and counts for pending, skipped, and automatically applied jobs. Previously-seen job URLs are not inserted again.

## Review, approve, and autofill

Review the HTML page, inspect each job link, then approve a particular job using its exact URL:

```powershell
python main.py approve "https://www.naukri.com/job-listings-example"
python main.py autofill "https://www.naukri.com/job-listings-example"
```

During `autofill`, navigate to the application form manually if needed and press Enter only when the form is visible. The tool fills only configured fields and attaches the configured résumé if an upload input is available. It prints missing fields/custom questions for manual attention, brings the application browser to the front, and waits. It does not locate or click the final application control. After you submit personally, type `applied` to record that confirmation. Any other response leaves the job approved.

### Optional 75% auto-apply mode

Your current config.yaml enables the requested auto-apply mode. It calculates a 0-100 résumé-fit score using target title (40 points), matching stack terms (up to 40), preferred location (10), and experience compatibility (10). Only results at or above 75 are considered:

```powershell
python main.py autoapply naukri
```

Before using it, complete every blank profile field in config.yaml. The run logs in manually once, searches, opens the application form, fills fields, and submits only where it recognizes the final submit button and finds no required empty fields. CAPTCHA/verification screens, missing profile data, unknown submit controls, and detected required unanswered fields remain pending in the local database; it does not try to circumvent them.

Useful commands:

```powershell
python main.py review
python main.py status
python main.py skip "https://www.naukri.com/job-listings-example"
```

## Customize matching and form fields

Edit `config.yaml` to change search keywords, locations, experience range, scoring terms, and exclusions. Search-site markup changes frequently; keep site-specific selector updates confined to `jobbot/scrapers/naukri.py` or `jobbot/scrapers/linkedin.py`. For uncommon questions, add a profile value and label fragments under `field_mapping`; the tool will otherwise list it as manual attention rather than guessing.

The default policy excludes insurance, frontend-only, DevOps-only, and cloud-engineer roles. Adjust these terms to your judgment; title/description snippets can be incomplete, so always use the review step.

## LinkedIn extension

After confirming Naukri works, log in manually and run:

```powershell
python main.py search linkedin
python main.py search indeed
```

LinkedIn and Indeed have separate adapters and persistent local browser profiles. Their DOM and application flows vary by account and job type, so validate results and tune the matching scraper selector file / `jobbot/autofill.py` as needed. The same tracking and 75% auto-apply controls apply. To search all three sites consecutively, use `python main.py search all`; to run the enabled auto-apply flow on each, use `python main.py autoapply all`.

## Safety and privacy

- No passwords or API credentials are stored.
- Every site action runs slowly in a visible browser (`action_delay_ms` and `search_delay_seconds` in the config). Do not reduce delays aggressively.
- CAPTCHA/login walls are deliberately manual intervention points.
- Files created at runtime are local: `.browser-data/`, `data/jobs.sqlite3`, and `outputs/daily-shortlist.html`.
