"""
Mira AI Videos Automation Pipeline
Prompts from: https://docs.google.com/document/d/1SEUWc7byF8wb0_FJGF_j68uskH68Elc-4PQT8wjMfmc/
Platform: Higgsfield (Seedance 2.0 text-to-video)
"""

import asyncio
import httpx
import os
import subprocess
import time
import json

# ── CONFIG ─────────────────────────────────────────────────────────────────
HIGGSFIELD_API_KEY    = os.environ.get("HIGGSFIELD_API_KEY", "")
HIGGSFIELD_API_SECRET = os.environ.get("HIGGSFIELD_API_SECRET", "")
BASE_URL = "https://platform.higgsfield.ai"

# Seedance 2.0 text-to-video model ID
SEEDANCE_MODEL = "bytedance/seedance/v2/lite/text-to-video"

OUTPUT_DIR = "C:/tmp/mira_pipeline"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── PROMPTS FROM MIRA AI DOC ──────────────────────────────────────────────
PROMPTS = [
    {
        "id": "clip1_influencer",
        "label": "Prompt #1 - Influencer Headphone Review",
        "prompt": (
            "A 38 year old woman, warm medium skin tone, shoulder-length dark brown hair worn loose and slightly wavy, "
            "deep brown almond-shaped eyes, soft features with a defined jawline, small gold stud earrings, wearing a "
            "forest green turtleneck sweater. She's standing in a modern lifestyle creator's home office — bright airy "
            "room with large windows letting in soft natural daylight, cream-coloured walls, a wooden desk in the "
            "background with a single potted plant and a stack of books, subtle minimalist styling, shallow depth of field. "
            "She's holding a pair of premium over-ear headphones in her hands — matte black finish with subtle brushed "
            "aluminium accents on the ear cups, soft tan-coloured premium leather padding. Medium shot, framed from the "
            "waist up. She's looking directly at the camera, speaking with warmth and confidence. Slight smile, engaging "
            "eye contact, like a top-tier YouTuber filming a product review. Cinematic depth of field. Native audio sync. "
            "No subtitles, no text, no captions. 16:9 horizontal format."
        ),
        "duration": 8,
        "aspect_ratio": "16:9"
    },
    {
        "id": "clip2_broll1",
        "label": "Prompt #2 - B-Roll Headphone Shot 1",
        "prompt": (
            "A pair of premium over-ear headphones sitting on a clean cream-coloured surface. Matte black finish with "
            "subtle brushed aluminium accents on the ear cups, soft tan-coloured premium leather padding on the headband "
            "and ear cushions, sleek minimalist industrial design with no visible logos. Slow cinematic camera push-in, "
            "slight rotation revealing the brushed aluminium ear cup detail. Soft directional studio lighting from the "
            "upper left casting gentle shadows. Sharp focus on the texture of the leather and brushed metal finish. "
            "Premium product cinematography. No audio, no music, no dialogue. 16:9 horizontal format."
        ),
        "duration": 5,
        "aspect_ratio": "16:9"
    },
    {
        "id": "clip3_broll2",
        "label": "Prompt #3 - B-Roll Headphone Shot 2",
        "prompt": (
            "A pair of premium over-ear headphones being folded flat by a pair of hands. Matte black finish with "
            "brushed aluminium accents, soft tan leather padding. Clean cream-coloured background, soft natural daylight. "
            "The hands twist and fold each ear cup inward, collapsing the headphones into a compact flat form. Slow "
            "cinematic motion, sharp focus on the folding mechanism and the texture of the leather and brushed metal. "
            "Premium product demo style. No audio, no music, no dialogue. 16:9 horizontal format."
        ),
        "duration": 5,
        "aspect_ratio": "16:9"
    }
]


# ── HIGGSFIELD API ────────────────────────────────────────────────────────

async def submit_video(client, prompt_data):
    model = SEEDANCE_MODEL
    url = f"{BASE_URL}/{model}"
    headers = {
        "Authorization": f"Key {HIGGSFIELD_API_KEY}:{HIGGSFIELD_API_SECRET}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "prompt": prompt_data["prompt"],
        "aspect_ratio": prompt_data["aspect_ratio"],
        "duration": prompt_data["duration"]
    }
    print(f"  Submitting: {prompt_data['label']}")
    resp = await client.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    print(f"  Queued — request_id: {data.get('request_id')}")
    return data["request_id"]


async def poll_status(client, request_id, label, max_wait=300):
    url = f"{BASE_URL}/requests/{request_id}/status"
    headers = {
        "Authorization": f"Key {HIGGSFIELD_API_KEY}:{HIGGSFIELD_API_SECRET}"
    }
    elapsed = 0
    while elapsed < max_wait:
        await asyncio.sleep(10)
        elapsed += 10
        resp = await client.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        print(f"  [{label}] {elapsed}s — status: {status}")
        if status == "completed":
            video_url = data.get("video", {}).get("url")
            print(f"  [{label}] Done! URL: {video_url}")
            return video_url
        elif status in ("failed", "nsfw"):
            raise RuntimeError(f"Generation {status} for {label}")
    raise TimeoutError(f"Timeout waiting for {label}")


async def download_video(url, out_path):
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
    print(f"  Downloaded: {out_path}")


def concatenate_videos(input_paths, output_path):
    list_file = os.path.join(OUTPUT_DIR, "filelist.txt")
    with open(list_file, "w") as f:
        for p in input_paths:
            f.write(f"file '{p}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]
    print(f"\nConcatenating {len(input_paths)} clips...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg stderr:", result.stderr[-500:])
        raise RuntimeError("ffmpeg concat failed")
    print(f"Final video: {output_path}")
    return output_path


async def run_pipeline():
    if not HIGGSFIELD_API_KEY:
        print("ERROR: HIGGSFIELD_API_KEY not set in environment.")
        print("Set it with: set HIGGSFIELD_API_KEY=your_key")
        print("And:         set HIGGSFIELD_API_SECRET=your_secret")
        return None

    print("=" * 60)
    print("MIRA AI VIDEO PIPELINE — Starting")
    print(f"Model: {SEEDANCE_MODEL}")
    print(f"Clips: {len(PROMPTS)}")
    print("=" * 60)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Step 1: Submit all 3 clips to queue
        print("\n[STEP 1] Submitting all clips to Higgsfield queue...")
        request_ids = []
        for p in PROMPTS:
            rid = await submit_video(client, p)
            request_ids.append(rid)
            await asyncio.sleep(1)

        # Step 2: Poll all clips for completion
        print("\n[STEP 2] Waiting for all clips to complete...")
        video_urls = []
        for i, (p, rid) in enumerate(zip(PROMPTS, request_ids)):
            url = await poll_status(client, rid, p["label"])
            video_urls.append(url)

    # Step 3: Download all clips
    print("\n[STEP 3] Downloading all clips...")
    local_paths = []
    for i, (p, url) in enumerate(zip(PROMPTS, video_urls)):
        out = os.path.join(OUTPUT_DIR, f"{i+1:02d}_{p['id']}.mp4")
        await download_video(url, out)
        local_paths.append(out)

    # Step 4: Concatenate into one final video
    print("\n[STEP 4] Concatenating into final video...")
    final_path = os.path.join(OUTPUT_DIR, "mira_final_headphone_review.mp4")
    concatenate_videos(local_paths, final_path)

    print("\n[DONE] Pipeline complete!")
    print(f"Final video: {final_path}")
    return final_path


if __name__ == "__main__":
    result = asyncio.run(run_pipeline())
    if result:
        # Copy to static folder for serving
        import shutil
        fname = os.path.basename(result)
        dst = f"C:/Users/Admin/OneDrive/Documents/max/static/files/{fname}"
        shutil.copy2(result, dst)
        pub_url = f"https://max.vdo-x.art/files/{fname}"
        print(f"\nPublic URL: {pub_url}")
        print("Send to Telegram with:")
        print(f"  python tools.py send_telegram '{{\"message\":\"{pub_url}\"}}'")
