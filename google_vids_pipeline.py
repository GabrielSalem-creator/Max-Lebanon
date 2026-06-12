"""
Mira AI Video Pipeline — Google Vids (Veo)
URL: https://docs.google.com/videos/create?usp=vids_alc&authuser=0
Uses pyautogui + Playwright browser automation to generate videos
"""

import asyncio
import time
import os
import re
import subprocess
import shutil
from playwright.async_api import async_playwright

OUTPUT_DIR = "C:/tmp/mira_veo"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GOOGLE_VIDS_URL = "https://docs.google.com/videos/create?usp=vids_alc&authuser=0"

PROMPTS = [
    {
        "id": "clip1_influencer",
        "label": "Influencer Headphone Review",
        "text": (
            "A 38 year old woman, warm medium skin tone, shoulder-length dark brown hair, "
            "deep brown almond-shaped eyes, wearing a forest green turtleneck sweater. "
            "Standing in a modern home office, holding premium over-ear headphones, "
            "speaking warmly to camera about the product. Cinematic, 16:9."
        )
    },
    {
        "id": "clip2_broll1",
        "label": "B-Roll Headphone Shot 1",
        "text": (
            "Premium over-ear headphones on a cream surface. Matte black, brushed aluminium, "
            "tan leather. Slow cinematic push-in revealing detail. Studio lighting. 16:9."
        )
    },
    {
        "id": "clip3_broll2",
        "label": "B-Roll Headphone Shot 2",
        "text": (
            "Hands folding premium over-ear headphones flat. Matte black finish, tan leather. "
            "Cream background, natural daylight. Slow cinematic motion. 16:9."
        )
    }
]


async def take_screenshot(page, name):
    path = f"C:/tmp/{name}.png"
    await page.screenshot(path=path)
    print(f"  Screenshot: {path}")
    return path


async def run_pipeline():
    print("=" * 60)
    print("MIRA AI VIDEO PIPELINE — Google Vids (Veo)")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch with existing Chrome profile so Google login is active
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="C:/Users/Admin/AppData/Local/Google/Chrome/User Data",
            executable_path="C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            headless=False,
            args=["--start-maximized", "--profile-directory=Default"]
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        print(f"\nNavigating to Google Vids...")
        await page.goto(GOOGLE_VIDS_URL, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(4)
        await take_screenshot(page, "vids_01_loaded")

        # Check what loaded
        title = await page.title()
        url = page.url
        print(f"  Title: {title}")
        print(f"  URL: {url}")

        # Check if we need to sign in
        content = await page.content()
        if "sign in" in content.lower() or "accounts.google.com" in url:
            print("  Need to sign in to Google first!")
            await take_screenshot(page, "vids_02_signin")
            await browser.close()
            return None

        await take_screenshot(page, "vids_02_interface")
        print(f"\n  Google Vids loaded. Analyzing interface...")

        # Look for text input or prompt field
        inputs = await page.query_selector_all("textarea, input[type=text], [contenteditable=true]")
        print(f"  Found {len(inputs)} input fields")

        # Try to find "Create with AI" or similar button
        buttons = await page.query_selector_all("button, [role=button]")
        button_texts = []
        for btn in buttons[:20]:
            txt = await btn.inner_text()
            if txt.strip():
                button_texts.append(txt.strip())
        print(f"  Buttons found: {button_texts}")

        await asyncio.sleep(2)
        await take_screenshot(page, "vids_03_explore")

        await browser.close()
        return "check_screenshots"


if __name__ == "__main__":
    asyncio.run(run_pipeline())
