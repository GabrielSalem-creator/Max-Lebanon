import asyncio
import json
import re
import httpx
from playwright.async_api import async_playwright

PROMPT = "a young boy playing football on a green field, dribbling and kicking the ball, sunny day, cinematic slow motion"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # intercept network requests to find the API call
        api_calls = []
        async def on_request(req):
            if 'api' in req.url or 'generat' in req.url or 'video' in req.url.lower():
                api_calls.append({'url': req.url, 'method': req.method})

        async def on_response(resp):
            if resp.status == 200 and ('video' in resp.url.lower() or 'generat' in resp.url.lower()):
                try:
                    body = await resp.text()
                    if 'http' in body and ('.mp4' in body or 'video' in body):
                        print("RESPONSE BODY:", body[:500])
                except:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

        print("Navigating to veoaifree.com...")
        await page.goto("https://veoaifree.com", timeout=30000, wait_until="networkidle")
        await asyncio.sleep(2)

        # find textarea or input for prompt
        print("Looking for prompt input...")
        textarea = await page.query_selector("textarea")
        if not textarea:
            textarea = await page.query_selector("input[type=text]")
        if not textarea:
            # try by placeholder
            textarea = await page.query_selector("[placeholder]")

        if textarea:
            print("Found input, filling prompt...")
            await textarea.click()
            await textarea.fill(PROMPT)
            await asyncio.sleep(1)

            # find generate button
            buttons = await page.query_selector_all("button")
            clicked = False
            for btn in buttons:
                text = await btn.inner_text()
                if any(kw in text.lower() for kw in ['generat', 'create', 'make', 'submit']):
                    print(f"Clicking button: {text.strip()}")
                    await btn.click()
                    clicked = True
                    break

            if not clicked:
                print("No generate button found, trying form submit...")
                await page.keyboard.press("Enter")

            print("Waiting for video generation (up to 120s)...")
            # wait for video element or download link
            try:
                await page.wait_for_selector("video, a[href*='.mp4'], a[download]", timeout=120000)
                print("Video element appeared!")
            except:
                print("Timeout waiting for video element")

            await asyncio.sleep(3)
            # check for video src
            video_el = await page.query_selector("video")
            if video_el:
                src = await video_el.get_attribute("src")
                print("VIDEO SRC:", src)

            # check for download links
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                if href and ('.mp4' in href or 'download' in (await link.get_attribute("class") or "")):
                    print("DOWNLOAD LINK:", href)

            # check page content for URLs
            content = await page.content()
            mp4_urls = re.findall(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', content)
            if mp4_urls:
                print("MP4 URLS FOUND:", mp4_urls)

            video_urls = re.findall(r'https?://[^\s"\'<>]+(?:video|vid)[^\s"\'<>]*', content)
            for url in video_urls[:5]:
                print("VIDEO URL:", url)

        else:
            print("ERROR: No text input found on page")
            # dump page HTML for debugging
            html = await page.content()
            print("PAGE SNIPPET:", html[:2000])

        print("\nAPI CALLS CAPTURED:")
        for call in api_calls:
            print(f"  {call['method']} {call['url']}")

        await browser.close()

asyncio.run(main())
