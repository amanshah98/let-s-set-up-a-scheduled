from __future__ import annotations
from pathlib import Path
import re

async def _first_field_for_label(page, label_fragment: str):
    # Try accessible labels before broad DOM heuristics. A mismatch is logged, not forced.
    locator = page.get_by_label(label_fragment, exact=False).first
    if await locator.count(): return locator
    locator = page.locator(f"input[placeholder*='{label_fragment}' i], textarea[placeholder*='{label_fragment}' i]").first
    return locator if await locator.count() else None

async def fill_application(page, profile: dict, mapping: dict) -> tuple[list[str], list[str]]:
    filled, manual = [], []
    for key, label_fragments in mapping.items():
        value = str(profile.get(key, "")).strip()
        if not value:
            manual.append(f"{key}: blank in config.yaml")
            continue
        field = None
        for fragment in label_fragments:
            field = await _first_field_for_label(page, fragment)
            if field: break
        if not field:
            manual.append(f"{key}: field not found")
            continue
        try:
            tag = await field.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                await field.select_option(label=value)
            else:
                await field.fill(value)
            filled.append(key)
        except Exception as exc:
            manual.append(f"{key}: {type(exc).__name__}")

    resume = Path(profile.get("resume_path", ""))
    if resume.is_file():
        upload = page.locator("input[type=file]").first
        if await upload.count():
            await upload.set_input_files(str(resume.resolve()))
            filled.append("resume attachment")
        else:
            manual.append("resume: upload control not found")
    else:
        manual.append("resume: path does not exist")
    return filled, manual

async def pause_before_submit(page, job_title: str) -> bool:
    # No locator is clicked here, including buttons that resemble the final action.
    await page.bring_to_front()
    print(f"\nAUTOFILL PAUSED for: {job_title}\nReview every field and answer screening questions in the browser. Click the final Submit/Apply yourself.")
    answer = input("After you personally submit, type 'applied' to log it; otherwise press Enter to leave it pending: ").strip().lower()
    return answer == "applied"

async def open_application_form(page) -> tuple[bool, str]:
    """Open the first-step form; this does not submit an application."""
    apply_button = page.get_by_role("button", name=re.compile(r"^(apply|apply now)$", re.I)).first
    if not await apply_button.count():
        return False, "Apply button not recognized; left pending"
    await apply_button.click()
    await page.wait_for_timeout(1_000)
    return True, "Application form opened"

async def submit_final_application(page) -> tuple[bool, str]:
    """Use only for explicit auto-apply mode; never bypass a CAPTCHA or questions."""
    body_text = (await page.locator("body").inner_text()).lower()
    if "captcha" in body_text or "verify you are human" in body_text:
        return False, "CAPTCHA/verification detected; left pending for manual action"
    submit_button = page.get_by_role(
        "button", name=re.compile(r"^(submit|submit application|send application)$", re.I)
    ).first
    if not await submit_button.count():
        return False, "Final submit button not recognized; left pending"
    required_empty = await page.locator("input[required], textarea[required], select[required]").evaluate_all(
        """fields => fields.filter(el => !el.value && !el.disabled).map(el => el.name || el.id || el.type)"""
    )
    if required_empty:
        return False, "Required fields need attention: " + ", ".join(required_empty)
    await submit_button.click()
    return True, "Submitted automatically after 75%+ match"
