"""Headless screenshots of the running app. Usage: python tools/shots.py [view ...]"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8080"
OUT = Path(__file__).resolve().parents[1] / "shots"
VIEWS = ["tutor", "practice", "materials", "duels", "admin"]


async def main(views: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1320, "height": 920}, device_scale_factor=2)
        await page.goto(BASE, wait_until="networkidle")
        # login (admin/admin)
        await page.fill("#afId", "admin")
        await page.fill("#afPass", "admin")
        await page.click("#afSubmit")
        await page.wait_for_selector("#app", state="visible", timeout=10000)
        await page.wait_for_timeout(900)
        for v in views:
            if v == "profile":  # not in the nav — reached via the account rail
                await page.click("#rail")
                await page.wait_for_timeout(400)
                await page.click("#umProfileBtn")
            else:
                await page.click(f'.nav__i[data-v="{v}"]')
            await page.wait_for_timeout(1400)
            shot = OUT / f"{v}.png"
            await page.screenshot(path=str(shot))
            print(f"saved {shot}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or VIEWS))
