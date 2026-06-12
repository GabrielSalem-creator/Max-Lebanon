import asyncio
import re
from playwright.async_api import async_playwright

PROMPT = "a young boy playing football on a green field, dribbling and kicking the ball, sunny day, cinematic"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        video_url = None
        api_responses = []

        async def handle_response(resp):
            nonlocal video_url
            try:
                ct = resp.headers.get("content-type", "")
                if "json" in ct or "text" in ct:
                    body = await resp.text()
                    if ".mp4" in body or "video_url" in body or "videoUrl" in body:
                        print(f"[RESP] {resp.url[:80]}")
                        print(f"[BODY] {body[:300]}")
                        urls = re.findall(r'https?://[^\s"\'\\<>]+\.mp4[^\s"\'\\<>]*', body)
                        if urls:
                            video_url = urls[0]
                            print(f"[VIDEO URL] {video_url}")
            except:
                pass

        page.on("response", handle_response)

        # Go directly to the generator page
        print("Opening generator page...")
        await page.goto("https://veoaifree.com/veo-video-generator/", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # Find and fill the prompt textarea
        ta = await page.query_selector("textarea")
        if not ta:
            ta = await page.query_selector("input[name='prompt'], input[placeholder*='prompt'], input[placeholder*='video'], input[placeholder*='describe']")
        if not ta:
            # get all inputs
            inputs = await page.query_selector_all("input[type=text], input:not([type]), textarea")
            if inputs:
                ta = inputs[0]

        if ta:
            await ta.click()
            await ta.fill(PROMPT)
            await asyncio.sleep(0.5)
            print(f"Filled prompt: {PROMPT}")
        else:
            print("No textarea found, dumping page...")
            html = await page.content()
            print(html[:3000])
            await browser.close()
            return

        # Find the generate button
        buttons = await page.query_selector_all("button, input[type=submit]")
        clicked = False
        for btn in buttons:
            txt = (await btn.inner_text()).strip().lower()
            val = await btn.get_attribute("value") or ""
            if any(kw in txt or kw in val.lower() for kw in ["generat", "create", "submit", "video"]):
                print(f"Clicking: {txt or val}")
                await btn.click()
                clicked = True
                break

        if not clicked:
            await page.keyboard.press("Enter")
            print("Pressed Enter")

        print("Waiting up to 180s for result...")
        deadline = 180
        interval = 3
        elapsed = 0
        while elapsed < deadline:
            await asyncio.sleep(interval)
            elapsed += interval

            # Check for video element
            vid = await page.query_selector("video")
            if vid:
                src = await vid.get_attribute("src") or await vid.get_attribute("data-src") or ""
                if src:
                    print(f"[VIDEO ELEMENT SRC] {src}")
                    video_url = src
                    break

            # Check for download/result links
            links = await page.query_selector_all("a[href*='.mp4'], a[download], a[href*='video']")
            for link in links:
                href = await link.get_attribute("href") or ""
                if ".mp4" in href or "download" in href:
                    print(f"[DOWNLOAD LINK] {href}")
                    video_url = href
                    break
            if video_url:
                break

            # Check page source
            content = await page.content()
            mp4s = re.findall(r'https?://[^\s"\'<>\\]+\.mp4[^\s"\'<>\\]*', content)
            if mp4s:
                video_url = mp4s[0]
                print(f"[PAGE SOURCE MP4] {video_url}")
                break

            # Check for error or loading state
            page_text = await page.evaluate("() => document.body.innerText")
            if "error" in page_text.lower() and elapsed > 10:
                print(f"[ERROR IN PAGE] {page_text[:200]}")

            if elapsed % 15 == 0:
                print(f"  Still waiting... {elapsed}s elapsed")
                # take a screenshot for debug
                await page.screenshot(path=f"C:/tmp/veo_debug_{elapsed}.png")

        if video_url:
            print(f"\nFINAL VIDEO URL: {video_url}")
        else:
            print("\nFailed to get video URL. Taking final screenshot...")
            await page.screenshot(path="C:/tmp/veo_final.png")
            html = await page.content()
            # look for any URL patterns
            all_urls = re.findall(r'https?://[^\s"\'<>\\]+', html)
            media_urls = [u for u in all_urls if any(ext in u for ext in ['.mp4', '.webm', 'video', 'media', 'download'])]
            for u in media_urls[:10]:
                print(f"  MEDIA URL: {u}")

        await browser.close()
        return video_url

result = asyncio.run(main())
print("RESULT:", result)
