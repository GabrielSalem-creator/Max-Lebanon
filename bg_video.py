#!/usr/bin/env python3
"""
Background video generation worker.
Usage: python3 bg_video.py '<json_params>'
Updates task DB and POSTs notification to /internal/notify when done.
"""
import json, requests, sys, time, uuid, sqlite3
from datetime import datetime, timezone
from pathlib import Path

TASKS_DB = str(Path(__file__).parent / "data" / "tasks.db")


def update_task(tid, status, result="", error=""):
    try:
        conn = sqlite3.connect(TASKS_DB)
        row = conn.execute("SELECT started_at FROM tasks WHERE id=?", (tid,)).fetchone()
        duration = None
        if row:
            try:
                started = datetime.fromisoformat(row[0])
                duration = (datetime.now(timezone.utc) - started).total_seconds()
            except Exception:
                pass
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE tasks SET status=?,completed_at=?,duration_s=?,result=?,error=? WHERE id=?",
            (status, now, duration, result, error, tid)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB update error: {e}")


def notify(message, room="default"):
    try:
        requests.post(
            "http://localhost:8000/internal/notify",
            json={"message": message, "room": room},
            timeout=5
        )
    except Exception:
        pass


def main():
    p = json.loads(sys.argv[1])
    tid = p.get("task_id", str(uuid.uuid4())[:8])
    prompt = p["prompt"]
    size = p.get("size", "16:9")
    with_audio = p.get("with_audio", False)
    room = p.get("room", "default")
    device_id = str(uuid.uuid4())

    session = requests.Session()
    session.headers.update({
        "accept": "*/*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7",
        "content-type": "application/json",
        "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-device-id": device_id,
        "referer": "https://www.nanobananavideo.io/en/generation/text-to-video?resolution=480P&aspectRatio=16%3A9&duration=3s&model=Free+Mode",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    })

    url = "https://www.nanobananavideo.io/api/generate-video"

    try:
        print(f"Starting video gen: {prompt}")
        r = session.post(url, json={
            "action": "generate",
            "prompt": prompt,
            "size": size,
            "withAudio": with_audio,
        }, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"Got response: {data}")

        task_id = data.get("taskId")
        if not task_id:
            msg = f"✗ No taskId in response: {str(data)[:200]}"
            update_task(tid, "failed", error=msg)
            notify(f"Video generation failed: {msg}", room)
            return

        # Poll using same session (cookies preserved)
        for i in range(60):
            time.sleep(3)
            try:
                pr = session.post(url, json={
                    "action": "check_status",
                    "taskId": task_id,
                    "prompt": "",
                    "size": size,
                    "withAudio": with_audio,
                }, timeout=30)
                j = pr.json()
                print(f"Poll {i+1}: {j.get('status', '?')}")
                status = j.get("status", "")

                if status in ("completed", "success", "done"):
                    video_url = j.get("videoUrl") or (j.get("result") or {}).get("videoUrl")
                    if video_url:
                        update_task(tid, "completed", result=video_url)
                        notify(f"🎬 Your video is ready! {video_url}", room)
                    else:
                        update_task(tid, "failed", error=f"No URL: {str(j)[:200]}")
                        notify(f"Video done but no URL found.", room)
                    return

                if status in ("failed", "error"):
                    msg = str(j)[:200]
                    update_task(tid, "failed", error=msg)
                    notify(f"Video generation failed: {msg}", room)
                    return

            except Exception as e:
                print(f"Poll error: {e}")

        update_task(tid, "failed", error="Timeout after ~3min")
        notify("Video generation timed out after 3 minutes.", room)

    except Exception as e:
        msg = str(e)
        update_task(tid, "failed", error=msg)
        notify(f"Video generation error: {msg}", room)


if __name__ == "__main__":
    main()
