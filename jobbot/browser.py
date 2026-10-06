from __future__ import annotations
from pathlib import Path
from playwright.async_api import BrowserContext, async_playwright

async def persistent_context(config: dict, source: str) -> tuple[object, BrowserContext]:
    """Launch a visible, persistent Chromium profile. Login is always manual."""
    runtime = config["runtime"]
    profile = Path(runtime["user_data_root"]) / source.lower()
    profile.mkdir(parents=True, exist_ok=True)
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        str(profile.resolve()), headless=runtime["headless"], slow_mo=runtime["action_delay_ms"]
    )
    return pw, context

async def wait_for_manual_login(page, login_url: str, source: str) -> None:
    await page.goto(login_url, wait_until="domcontentloaded")
    print(f"\nLog into {source} in the opened browser. Complete any CAPTCHA yourself.")
    input("When you can see the site while logged in, press Enter here to continue... ")
