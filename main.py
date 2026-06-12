import asyncio
import json
import re
import sys
import os
import time
import uuid as _uuid_mod
import subprocess as _sp
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

app = FastAPI(title="MAX")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC = Path(__file__).parent / "static"
MAX_DIR = Path(__file__).parent

# Detect claude binary cross-platform
if sys.platform == "win32":
    _win_claude = Path(os.environ.get("APPDATA","")) / "npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
    CLAUDE_BIN = str(_win_claude) if _win_claude.exists() else "claude"
else:
    CLAUDE_BIN = "/home/boxd/.local/bin/claude"

# ── FAST conversational LLM (qwen via hidns) — Track 1 instant responder ───
QWEN_URL    = "https://chat.good.hidns.vip/api/openai/v1/chat/completions"
QWEN_MODEL  = os.environ.get("QWEN_MODEL", "qwen3.6-plus")
QWEN_COOKIE_FILE = Path(__file__).parent / "data" / "qwen_cookie.txt"

def _qwen_cookie() -> str:
    """Read the browser session cookie for the fast LLM (user pastes it once)."""
    env = os.environ.get("QWEN_COOKIE", "").strip()
    if env:
        return env
    try:
        return QWEN_COOKIE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""

# Legacy alias (kept so old code paths don't break)
LLM_URL   = os.environ.get("LLM_URL",   "https://chat.good.hidns.vip/api/openai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")

PLAN_RE  = re.compile(r"MAX_PLAN:\s*(\{[\s\S]*?\})", re.MULTILINE)
SENT_RE  = re.compile(r"(.+?[.!?]+)\s+")
INPUT_RE = re.compile(
    r"\b(enter|type|provide|input|give|tell|submit|paste|need)\b.{0,140}"
    r"\b(code|password|token|key|pin|otp|captcha|2fa|verification|confirm|secret|auth)\b",
    re.IGNORECASE,
)

# Task verbs → must go through full claude agent
_TASK_VERBS = frozenset({
    "generate", "make", "create", "open", "close", "launch", "send", "search",
    "find", "download", "click", "drag", "type", "write", "build", "run",
    "install", "delete", "move", "copy", "edit", "update", "start", "stop",
    "browse", "navigate", "screenshot", "video", "image", "email", "telegram",
    "powerpoint", "play", "control", "automate", "login", "translate", "convert",
    "schedule", "book", "buy", "order", "post", "upload", "deploy", "execute",
    "extract", "scrape", "summarize", "record", "print", "save", "draw", "read",
    "get me", "show me", "pull", "fetch", "check", "monitor",
})

def _is_agentic(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in _TASK_VERBS)

# Shared state
rooms:    dict[str, list[WebSocket]] = {}
sessions: dict[str, Optional[str]]   = {}
_active:  dict[str, int]             = {}
_stop:    dict[str, bool]            = {}
_mute:    dict[str, bool]            = {}   # "shut up" → stop sending TTS (task keeps running)
_procs:   dict[str, list]            = {}

# PID tracking — every python process MAX spawns is recorded here
_server_pid = os.getpid()                  # never kill this one
_task_pids:  dict[str, list[int]] = {}     # room -> [pids spawned during current tasks]

# Task registry
_registry: dict[str, dict] = {}

# ── INSTANT-ANSWER CACHE — prefetched facts, zero LLM latency ──────────────
# Refreshed on startup + on a schedule. User questions matching these are
# answered DIRECTLY from cache — no model call at all.
FACTS_FILE  = Path(__file__).parent / "data" / "fast_facts.json"
_fast_facts: dict = {}
USER_LAT = float(os.environ.get("USER_LAT", "33.8938"))   # Beirut default
USER_LON = float(os.environ.get("USER_LON", "35.5018"))
USER_CITY = os.environ.get("USER_CITY", "Beirut")


def _kill_pid_tree(pid: int):
    """Kill a process and all its children (Windows /T flag)."""
    try:
        _sp.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=3)
    except Exception:
        pass


def _kill_task_pids(room: str):
    """Kill all PIDs tracked for a room's tasks, then clear the list."""
    pids = _task_pids.pop(room, [])
    for pid in pids:
        if pid and pid != _server_pid:
            _kill_pid_tree(pid)


def _kill_stray_pythons():
    """Kill every python.exe that MAX spawned but that isn't the server itself."""
    try:
        out = _sp.run(
            ["wmic", "process", "where", "name='python.exe'",
             "get", "ProcessId", "/format:csv"],
            capture_output=True, text=True, timeout=5
        ).stdout
        for line in out.splitlines():
            parts = line.strip().split(",")
            if parts and parts[-1].isdigit():
                pid = int(parts[-1])
                if pid != _server_pid:
                    _kill_pid_tree(pid)
    except Exception:
        pass

SCREEN_FILE = Path(__file__).parent / "data" / "last_screen.jpg"

# ── Direct Anthropic API (bypasses CLI startup overhead) ───────────────────
ANTHROPIC_API  = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-sonnet-4-6"
_api_token: Optional[str] = None   # loaded lazily from credentials
_max_system: Optional[str] = None  # loaded from CLAUDE.md
histories:  dict[str, list] = {}   # room -> current turn messages
_summaries: dict[str, str]  = {}   # room -> one-line rolling recap of prior context
_claude_talking: dict[str, bool] = {}   # room -> True once Claude starts responding (mutes chat-z filler)

BASH_TOOL = {
    "name": "bash",
    "description": (
        "Execute any shell command, Python script, or tools.py call. "
        "Use for ALL tool calls: python tools.py ..., start commands, PowerShell, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout": {"type": "integer", "default": 60},
        },
        "required": ["command"],
    },
}


def _get_api_token() -> Optional[str]:
    global _api_token
    if _api_token:
        return _api_token
    creds = Path(os.environ.get("USERPROFILE", "")) / ".claude" / ".credentials.json"
    try:
        data = json.loads(creds.read_text(encoding="utf-8"))
        _api_token = data.get("claudeAiOauth", {}).get("accessToken")
    except Exception:
        pass
    return _api_token


def _get_system() -> str:
    global _max_system
    if not _max_system:
        p = MAX_DIR / "CLAUDE.md"
        _max_system = p.read_text(encoding="utf-8") if p.exists() else "You are MAX, an autonomous AI assistant."
    return _max_system


async def _exec_bash(cmd: str, timeout: int = 60, room: str = "") -> str:
    """Run a shell command, track PID, return combined stdout+stderr (max 3000 chars)."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(MAX_DIR),
        )
        # Track the PID so we can kill it when the task finishes
        if room and proc.pid and proc.pid != _server_pid:
            _task_pids.setdefault(room, []).append(proc.pid)

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            _kill_pid_tree(proc.pid)
            return f"[timed out after {timeout}s — process killed]"

        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        result = out or err or "(no output)"
        if out and err:
            result = f"{out}\n[stderr: {err[:300]}]"
        return result[:3000]
    except Exception as e:
        return f"[error: {e}]"


def _reg_add(room: str, desc: str, proc=None) -> str:
    """Register a new task and return its ID."""
    tid = _uuid_mod.uuid4().hex[:8]
    _registry[tid] = {
        "id": tid, "room": room,
        "desc": desc[:80],
        "started": time.time(),
        "pid": proc.pid if proc else None,
        "status": "running",
    }
    return tid


def _reg_done(tid: str, status: str = "done"):
    if tid in _registry:
        _registry[tid]["status"] = status


def _reg_kill(tid: str):
    """Kill the process attached to a task and mark it stopped."""
    t = _registry.get(tid)
    if not t:
        return
    if t.get("pid"):
        try:
            import subprocess as _sp
            _sp.run(["taskkill", "/F", "/PID", str(t["pid"])],
                    capture_output=True, timeout=3)
        except Exception:
            pass
    t["status"] = "stopped"

# Proactive engagement state
last_activity:  dict[str, float] = {}     # room -> epoch of last user message
last_proactive: dict[str, float] = {}     # room -> epoch of last proactive push

SILENCE_SECS      = 300   # 5 min idle before proactive message
PROACTIVE_COOLDOWN = 600  # 10 min minimum between proactive messages
NEWS_FILE = Path(__file__).parent / "data" / "daily_news.json"

app.mount("/img", StaticFiles(directory=str(STATIC / "img")), name="img")
app.mount("/files", StaticFiles(directory=str(STATIC / "files")), name="files")


@app.get("/")
async def root():
    return HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"))


@app.get("/tts")
async def tts(text: str = Query(...)):
    import edge_tts

    async def gen():
        comm = edge_tts.Communicate(text[:500], voice="en-US-JennyNeural")
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(gen(), media_type="audio/mpeg")


@app.get("/desktop/snapshot")
async def desktop_snapshot():
    try:
        import pyautogui
        from io import BytesIO
        loop = asyncio.get_event_loop()
        screenshot = await loop.run_in_executor(None, pyautogui.screenshot)
        buf = BytesIO()
        await loop.run_in_executor(None, lambda: screenshot.save(buf, format="JPEG", quality=50))
        buf.seek(0)
        return Response(
            content=buf.read(),
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store, no-cache", "Pragma": "no-cache"},
        )
    except Exception:
        return Response(status_code=503)


TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_FILE = Path(__file__).parent / "data" / "tg_chat_id.txt"


@app.post("/telegram/webhook")
async def telegram_webhook(data: dict = Body(...)):
    msg = data.get("message") or data.get("edited_message") or {}
    chat_id = str(msg.get("chat", {}).get("id", ""))
    if chat_id:
        TG_CHAT_FILE.parent.mkdir(exist_ok=True)
        TG_CHAT_FILE.write_text(chat_id)
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": "MAX connected! I'll send you notifications here."}
            )
    return {"ok": True}


@app.post("/internal/notify")
async def internal_notify(data: dict = Body(...)):
    """Background workers call this to push notifications to all WS clients."""
    message = data.get("message", "")
    room = data.get("room", "default")
    if message:
        payload = {"type": "notification", "text": message}
        for ws in list(rooms.get(room, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                pass
    return {"ok": True}


# ── Fast LLM cookie config ─────────────────────────────────────────────────

@app.get("/api/qwen-status")
async def qwen_status():
    cookie = _qwen_cookie()
    if not cookie:
        return {"configured": False, "working": False}
    # Quick test ping
    import httpx
    try:
        async with httpx.AsyncClient(timeout=12) as c:
            r = await c.post(QWEN_URL,
                headers={"content-type": "application/json", "cookie": cookie,
                         "origin": "https://chat.good.hidns.vip",
                         "referer": "https://chat.good.hidns.vip/"},
                json={"model": QWEN_MODEL, "stream": False,
                      "messages": [{"role": "user", "content": "hi"}],
                      "max_completion_tokens": 10})
            ok = r.status_code == 200 and bool(
                r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            return {"configured": True, "working": ok}
    except Exception:
        return {"configured": True, "working": False}


@app.post("/api/qwen-cookie")
async def set_qwen_cookie(data: dict = Body(...)):
    cookie = (data.get("cookie") or "").strip()
    QWEN_COOKIE_FILE.parent.mkdir(exist_ok=True)
    QWEN_COOKIE_FILE.write_text(cookie, encoding="utf-8")
    os.environ["QWEN_COOKIE"] = cookie
    return {"ok": True, "len": len(cookie)}


# ── Task manager API ───────────────────────────────────────────────────────

@app.get("/api/tasks")
async def api_tasks():
    """Return all tasks (running, recent done/stopped)."""
    now = time.time()
    # Prune tasks older than 5 min that aren't running
    for tid in list(_registry):
        t = _registry[tid]
        if t["status"] != "running" and now - t["started"] > 300:
            del _registry[tid]
    return {"tasks": list(_registry.values())}


@app.post("/api/tasks/{tid}/stop")
async def api_stop_task(tid: str):
    _reg_kill(tid)
    return {"ok": True, "id": tid}


@app.post("/api/tasks/stop-all")
async def api_stop_all(data: dict = Body(default={})):
    room = data.get("room", "default")
    _stop[room] = True
    _kill_room_procs(room)
    for t in _registry.values():
        if t["room"] == room and t["status"] == "running":
            t["status"] = "stopped"
    return {"ok": True}


# ── Proactive engagement: news fetch + silence monitor ─────────────────────

async def _fetch_daily_news():
    """Scrape top headlines and cache to disk. Runs once per day."""
    from datetime import date
    today = str(date.today())
    if NEWS_FILE.exists():
        try:
            cached = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
            if cached.get("date") == today and cached.get("items"):
                return  # already fresh
        except Exception:
            pass
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", str(MAX_DIR / "tools.py"), "search",
            '{"query":"top news headlines today world breaking","num_results":10}',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            cwd=str(MAX_DIR),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=40)
        raw = stdout.decode(errors="replace").strip()
        NEWS_FILE.parent.mkdir(exist_ok=True)
        NEWS_FILE.write_text(
            json.dumps({"date": today, "items": raw}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


async def _silence_monitor():
    """Every 30 s: if a room has been silent 5+ min, proactively share news."""
    await asyncio.sleep(90)          # let server fully start up
    asyncio.create_task(_fetch_daily_news())
    while True:
        await asyncio.sleep(30)
        now = time.time()
        for room, clients in list(rooms.items()):
            if not clients:
                continue
            silent_for    = now - last_activity.get(room, now)
            since_pro     = now - last_proactive.get(room, 0)
            if silent_for < SILENCE_SECS or since_pro < PROACTIVE_COOLDOWN:
                continue
            # User is idle — read news to them
            try:
                if not NEWS_FILE.exists():
                    continue
                nd = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
                items = str(nd.get("items", ""))[:2500]
                if not items:
                    continue
                last_proactive[room] = now
                last_activity[room]  = now  # prevent re-triggering immediately
                ws = clients[0]
                prompt = (
                    "SYSTEM_PROACTIVE: The user has been quiet. "
                    "Deliver today's most interesting news highlights in a warm, engaging, conversational way. "
                    "Open naturally (e.g. 'Hey, while you have a moment…'). "
                    "Pick the 3 most interesting stories. Keep it under 60 seconds of speech. "
                    f"News data: {items}"
                )
                asyncio.create_task(run_msg(prompt, ws, room))
            except Exception:
                pass


async def _refresh_fast_facts():
    """Fetch weather + news headlines into the instant-answer cache. Runs hourly."""
    import httpx
    facts = dict(_fast_facts)
    # Weather (open-meteo, no key)
    try:
        async with httpx.AsyncClient(timeout=12) as c:
            r = await c.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": USER_LAT, "longitude": USER_LON,
                        "current": "temperature_2m,weather_code,wind_speed_10m",
                        "daily": "temperature_2m_max,temperature_2m_min",
                        "timezone": "auto", "forecast_days": 1},
            )
            d = r.json()
            cur = d.get("current", {})
            day = d.get("daily", {})
            code = cur.get("weather_code", 0)
            cond = _WEATHER_CODES.get(code, "variable conditions")
            temp = round(cur.get("temperature_2m", 0))
            hi = round(day.get("temperature_2m_max", [temp])[0])
            lo = round(day.get("temperature_2m_min", [temp])[0])
            facts["weather"] = (
                f"In {USER_CITY} right now it's about {temp} degrees with {cond}. "
                f"Today's high is around {hi} and the low is about {lo}."
            )
    except Exception:
        pass
    # News headlines (from the daily cache if present)
    try:
        if NEWS_FILE.exists():
            nd = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
            items = str(nd.get("items", "")).strip()
            if len(items) > 80:
                facts["news"] = items[:1500]
    except Exception:
        pass
    facts["updated"] = time.time()
    _fast_facts.clear()
    _fast_facts.update(facts)
    try:
        FACTS_FILE.parent.mkdir(exist_ok=True)
        FACTS_FILE.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


CHATZ_URL = "https://chat-z.created.app/api/chat"

async def _chat_z(prompt: str, timeout: int = 18) -> str:
    """Free no-auth conversational LLM — the talking layer. Returns content or ''."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(CHATZ_URL, json={"prompt": prompt},
                             headers={"Content-Type": "application/json"})
            if r.status_code == 200:
                d = r.json()
                if d.get("success"):
                    content = (d.get("content") or "").strip()
                    if content and content.lower() not in ("no content found", ""):
                        return content
    except Exception:
        pass
    return ""


async def _search_raw(query: str) -> str:
    """Run the search tool, return raw text result."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", str(MAX_DIR / "tools.py"), "search",
            json.dumps({"query": query, "num_results": 6}),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            cwd=str(MAX_DIR),
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=35)
        return out.decode(errors="replace").strip()
    except Exception:
        return ""


async def _summarize(raw: str, instruction: str) -> str:
    """One-time background summarization via free chat-z LLM → clean spoken text."""
    if not raw:
        return ""
    prompt = (
        f"{instruction}\n\n"
        "Reply in warm spoken sentences. No markdown, no symbols, no URLs, no lists. "
        "Keep it under 110 words.\n\n"
        f"Data:\n{raw[:2200]}"
    )
    return await _chat_z(prompt, timeout=25)


# Topic → (search query, summarization instruction, cache key)
LEBANON_TOPICS = [
    ("best restaurants Beirut Lebanon phone number opening hours 2026",
     "List 4 good restaurants in Beirut. For each give the name, the area, and the kind of food. "
     "Mention opening hours or a phone number only if the data clearly shows it. Be conversational.",
     "leb_restaurants"),
    ("fun things to do Lebanon summer 2026 activities beaches nightlife",
     "Suggest 4 cool things to do in Lebanon this summer. Be specific and exciting.",
     "leb_activities"),
    ("Lebanon travel safety 2026 which regions safe to visit advisory",
     "Summarize which parts of Lebanon are generally considered safe to visit and which to avoid, "
     "based on this data. End with: always check the latest advisory before you travel.",
     "leb_safety"),
    ("Lebanon news today breaking headlines",
     "Give the 3 biggest Lebanon news stories today, conversationally.",
     "leb_news"),
]


async def _prefetch_lebanon():
    """Search + summarize-once + cache all Lebanon topics. Real data, instant serving."""
    async def one(query, instruction, key):
        raw = await _search_raw(query)
        if not raw:
            return
        summary = await _summarize(raw, instruction)
        if summary:
            _fast_facts[key] = summary

    await asyncio.gather(*[one(q, i, k) for q, i, k in LEBANON_TOPICS],
                         return_exceptions=True)
    # Build today/tomorrow schedule from file (user-editable) or default
    _load_schedule()
    try:
        FACTS_FILE.parent.mkdir(exist_ok=True)
        FACTS_FILE.write_text(json.dumps(_fast_facts, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _load_schedule():
    """Read data/schedule.json (user-editable) → spoken summary cached as 'schedule'."""
    from datetime import datetime, timedelta
    sf = MAX_DIR / "data" / "schedule.json"
    try:
        if sf.exists():
            data = json.loads(sf.read_text(encoding="utf-8"))
        else:
            data = {"today": [], "tomorrow": []}
            sf.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        data = {"today": [], "tomorrow": []}
    today = data.get("today", [])
    tom = data.get("tomorrow", [])
    if not today and not tom:
        _fast_facts["schedule"] = (
            "Your schedule is open today and tomorrow. "
            "Want me to add something? Just tell me."
        )
        return
    parts = []
    if today:
        parts.append("Today you have " + ", then ".join(today) + ".")
    else:
        parts.append("Today is open.")
    if tom:
        parts.append("Tomorrow you have " + ", then ".join(tom) + ".")
    _fast_facts["schedule"] = " ".join(parts)


async def _fast_facts_loop():
    await asyncio.sleep(2)
    await _refresh_fast_facts()
    await _prefetch_lebanon()          # initial fill
    while True:
        await asyncio.sleep(3600)      # hourly
        await _refresh_fast_facts()
        await _prefetch_lebanon()


_WEATHER_CODES = {
    0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
    81: "rain showers", 82: "violent rain showers", 95: "thunderstorms",
    96: "thunderstorms with hail", 99: "severe thunderstorms",
}

_MONTHS = ["January","February","March","April","May","June","July",
           "August","September","October","November","December"]
_DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
_NUM_WORDS = ["zero","one","two","three","four","five","six","seven","eight","nine","ten",
              "eleven","twelve"]


def _spell_minute(m: int) -> str:
    if m == 0: return "o'clock"
    if m < 10: return f"oh {_NUM_WORDS[m]}" if m < len(_NUM_WORDS) else f"oh {m}"
    return str(m)


async def _youtube_first_watch(q: str) -> str:
    """Fetch the first matching video ID from YouTube search and return its autoplay watch URL.
    Falls back to the results page if the scrape fails. Adds ~300-500ms — still flash."""
    from urllib.parse import quote
    results_url = f"https://www.youtube.com/results?search_query={quote(q)}"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=6, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }) as c:
            r = await c.get(results_url)
            if r.status_code == 200:
                # First videoId in the search payload is the top result.
                m = re.search(r'"videoId":"([\w-]{11})"', r.text)
                if m:
                    return f"https://www.youtube.com/watch?v={m.group(1)}"
    except Exception:
        pass
    return results_url


def _try_instant_action(text: str):
    """Return (shell_command, spoken_reply) for instant actions — no LLM. Flash speed."""
    from urllib.parse import quote
    t = text.lower().strip()

    # ── YouTube: open + play/search ──
    if "youtube" in t or re.search(r"\bplay\b", t):
        q = text
        # drop domains/URLs first so ".com" doesn't leak into the query
        q = re.sub(r"(?i)\b(?:www\.)?youtu(?:be)?\.(?:com|be)\b", " ", q)
        q = re.sub(r"(?i)\.com\b|\bdot com\b", " ", q)
        # strip command/filler words to isolate the actual query
        q = re.sub(r"(?i)\b(hey\s+max|max|can you|could you|would you|please|open|go to|launch|and|on|in|the|a|to|play|put on|youtube|video|music|song|track|for me|some|search for|search)\b", " ", q)
        q = re.sub(r"\s+", " ", q).strip(" ,.-")
        if q:
            # Signal: resolve the FIRST matching video and open its watch page (auto-plays).
            return (f"__yt_play__:{q}", f"Playing {q} on YouTube.")
        return ('start chrome "https://www.youtube.com"', "Opening YouTube.")

    # ── Known sites: "open X" / "go to X" ──
    SITES = {
        "gmail": "https://mail.google.com", "email": "https://mail.google.com",
        "whatsapp": "https://web.whatsapp.com", "instagram": "https://instagram.com",
        "facebook": "https://facebook.com", "twitter": "https://twitter.com",
        "x": "https://x.com", "google": "https://google.com",
        "maps": "https://maps.google.com", "spotify": "https://open.spotify.com",
        "netflix": "https://netflix.com", "chatgpt": "https://chat.openai.com",
        "reddit": "https://reddit.com", "tiktok": "https://tiktok.com",
        "linkedin": "https://linkedin.com", "github": "https://github.com",
    }
    m = re.search(r"(?i)\b(?:open|go to|launch|bring up)\s+(.+)", text)
    if m:
        target = m.group(1).lower().strip(" ,.-")
        # match site names as WHOLE WORDS only — never as substrings, so "x" can't
        # match the letter x inside "explorer"/"max"/"next".
        target_words = set(re.findall(r"[a-z0-9]+", target))
        for name, url in SITES.items():
            if name in target_words:
                return (f'start chrome "{url}"', f"Opening {name}.")
        # bare domain like "open example.com"
        dm = re.search(r"([a-z0-9-]+\.[a-z]{2,})", target)
        if dm:
            return (f'start chrome "https://{dm.group(1)}"', f"Opening {dm.group(1)}.")

    # ── Windows apps ──
    APPS = {
        "notepad": "notepad", "calculator": "calc", "calc": "calc",
        "settings": "start ms-settings:", "explorer": "explorer",
        "file explorer": "explorer", "paint": "mspaint", "task manager": "taskmgr",
        "camera": "start microsoft.windows.camera:", "terminal": "wt",
    }
    if re.search(r"(?i)\b(open|launch|start)\b", t):
        for name, cmd in APPS.items():
            if name in t:
                full = cmd if cmd.startswith("start") else f"start {cmd}"
                return (full, f"Opening {name}.")

    return None


_STATUS_PATTERNS = (
    "where is", "is it ready", "is it done", "did it finish", "did you finish",
    "is it finished", "what's the status", "whats the status", "are you done",
    "finished yet", "is it working", "how long", "how much longer", "is it generated",
    "did you make", "did you send", "did you generate", "still working", "what happened to",
)

def _is_status_query(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in _STATUS_PATTERNS)


def _task_status_report(room: str) -> Optional[str]:
    """Build a spoken status report from the task registry. None if no relevant tasks."""
    now = time.time()
    running = [t for t in _registry.values()
               if t["room"] == room and t["status"] == "running"]
    recent = [t for t in _registry.values()
              if t["room"] == room and t["status"] in ("done", "failed", "stopped")]
    recent.sort(key=lambda t: t["started"], reverse=True)

    if running:
        parts = []
        for t in running:
            el = int(now - t["started"])
            desc = t["desc"].replace("chat: ", "")
            parts.append(f"I'm still working on {desc} — it's been about {el} seconds")
        return ". ".join(parts) + ". Almost there."

    if recent:
        t = recent[0]
        el = int(t["started"] - now) * -1
        desc = t["desc"].replace("chat: ", "")
        if t["status"] == "done":
            res = t.get("result", "")
            extra = f" {res}" if res else ""
            return f"I finished {desc} a moment ago.{extra}"
        if t["status"] == "failed":
            return f"I tried {desc} but it ran into a problem. Want me to try again?"
        if t["status"] == "stopped":
            return f"That task — {desc} — was stopped."
    return None


def _try_instant_answer(text: str) -> Optional[str]:
    """Return a cached answer instantly (no LLM) if the question matches a known fact."""
    from datetime import datetime
    t = text.lower().strip()

    # ── LEBANON cached topics (prefetched + pre-summarized) ──
    lf = _fast_facts
    if any(p in t for p in ("restaurant", "where to eat", "where can i eat", "place to eat", "food place", "dinner", "lunch spot")):
        if lf.get("leb_restaurants"):
            return lf["leb_restaurants"]
    if any(p in t for p in ("things to do", "activity", "activities", "what to do", "fun", "summer", "cool to do", "go out")):
        if lf.get("leb_activities"):
            return lf["leb_activities"]
    if any(p in t for p in ("safe", "danger", "region", "war", "avoid", "risky", "secure area")):
        if lf.get("leb_safety"):
            return lf["leb_safety"]
    if any(p in t for p in ("lebanon news", "news lebanon", "what's happening", "whats happening", "headlines")):
        if lf.get("leb_news"):
            return lf["leb_news"]
    if any(p in t for p in ("my schedule", "what do i have", "my day", "my plan", "agenda", "today and tomorrow", "what's on")):
        if lf.get("schedule"):
            return lf["schedule"]

    # TIME — computed live, zero latency
    if any(p in t for p in ("what time", "what's the time", "whats the time", "current time", "time is it", "time right now")):
        now = datetime.now()
        h12 = now.hour % 12 or 12
        ampm = "AM" if now.hour < 12 else "PM"
        mtext = _spell_minute(now.minute)
        return f"It's {h12} {mtext} {ampm}."

    # DATE / DAY
    if any(p in t for p in ("what day", "what's the date", "whats the date", "today's date", "what date", "which day")):
        now = datetime.now()
        return f"Today is {_DAYS[now.weekday()]}, {_MONTHS[now.month-1]} {now.day}."

    # WEATHER — from cache
    if any(p in t for p in ("weather", "temperature", "how hot", "how cold", "is it raining", "forecast")):
        w = _fast_facts.get("weather")
        if w:
            return w

    return None


@app.on_event("startup")
async def _startup():
    asyncio.create_task(_silence_monitor())
    asyncio.create_task(_continuous_screen_capture())
    asyncio.create_task(_fast_facts_loop())


async def _capture_screen():
    """Take one screenshot and save to data/last_screen.jpg."""
    try:
        import pyautogui
        from io import BytesIO
        loop = asyncio.get_event_loop()
        shot = await loop.run_in_executor(None, pyautogui.screenshot)
        buf = BytesIO()
        await loop.run_in_executor(None, lambda: shot.save(buf, format="JPEG", quality=60))
        buf.seek(0)
        SCREEN_FILE.parent.mkdir(exist_ok=True)
        SCREEN_FILE.write_bytes(buf.read())
    except Exception:
        pass


async def _continuous_screen_capture():
    """Refresh last_screen.jpg every 10 s — low overhead, always reasonably current."""
    await asyncio.sleep(20)
    while True:
        await _capture_screen()
        await asyncio.sleep(10)


_FILLERS = [
    "Still on it — should be done shortly. By the way, want to hear what's happening in Lebanon today, or plan your next road trip?",
    "Working on that now. While I finish — want me to check your calendar, set something new, or just tell you a quick joke?",
    "Still going. Want to know the latest news, plan something for tonight, or hear something interesting while you wait?",
    "Almost there. Want me to pull up your calendar, recommend something to do, or share a fun fact while I wrap this up?",
]

async def _send_tts(ws: WebSocket, room: str, text: str):
    """Send one TTS line — unless the room is muted ('shut up')."""
    if _mute.get(room):
        return
    await safe_send(ws, {"type": "tts", "text": text})


async def _say(ws: WebSocket, text: str, room: str = ""):
    """Send a line to UI + speak it (TTS suppressed if the room is muted)."""
    await safe_send(ws, {"type": "event", "data": {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }})
    if _mute.get(room):
        return
    clean = _clean_for_tts(text)
    for m in SENT_RE.finditer(clean + " "):
        s = m.group(1).strip()
        if len(s) > 3:
            await _send_tts(ws, room, s)


async def _task_filler(ws: WebSocket, room: str, task_desc: str = "", delay: float = 8.0):
    """Keep the user company while the task runs — ONE warm opener, then occasional brief
    reassurance. Never volunteers Lebanon tips. Stops the moment the room is muted/stopped."""
    round_n = 0
    try:
        # First line: acknowledge + rough time estimate (only if not muted/stopped)
        await asyncio.sleep(delay)
        if _stop.get(room) or _mute.get(room):
            return
        opener = await _chat_z(
            "You are MAX, a warm voice assistant. A task is running in the background for the user. "
            f"The task is: {task_desc[:80]}. "
            "Say ONE short warm sentence telling them you're on it and roughly how long it might take. "
            "Do not suggest topics, do not mention Lebanon, do not ask questions. Spoken style, no markdown.",
            timeout=12,
        )
        await _say(ws, opener or "On it — this'll just take a moment.", room)

        # Occasional brief reassurance (every ~25s). Stops on mute or stop. No Lebanon, no chatter.
        while not _stop.get(room) and not _mute.get(room):
            await asyncio.sleep(25)
            if _stop.get(room) or _mute.get(room):
                return
            round_n += 1
            if round_n > 4:   # cap: don't nag forever
                return
            await _say(ws, "Still working on it — almost there.", room)
    except asyncio.CancelledError:
        pass


def _kill_room_procs(room: str):
    """Terminate all tracked subprocesses for a room."""
    for proc in _procs.pop(room, []):
        try:
            proc.terminate()
        except Exception:
            pass


@app.websocket("/ws")
async def ws_handler(ws: WebSocket, room: str = "default"):
    await ws.accept()
    ws._room = room   # tag socket so safe_send can mute TTS per-room
    rooms.setdefault(room, []).append(ws)
    sessions.setdefault(room, None)

    try:
        while True:
            data = await ws.receive_json()
            t = data.get("type")

            if t == "message":
                last_activity[room] = time.time()
                _stop[room] = False   # clear any previous stop flag
                _mute[room] = False   # a new request un-mutes TTS
                await broadcast(room, {"type": "user_message", "text": data["text"]}, exclude=ws)
                asyncio.create_task(run_msg(data["text"], ws, room))

            elif t == "mute_tts":
                # "shut up" / "stop talking" — silence TTS only; the task keeps running.
                _mute[room] = True
                await ws.send_json({"type": "muted"})

            elif t == "stop":
                _stop[room] = True
                _kill_room_procs(room)
                _kill_task_pids(room)
                asyncio.get_event_loop().run_in_executor(None, _kill_stray_pythons)
                await ws.send_json({"type": "stopped", "text": "All tasks stopped."})

            elif t == "reset":
                sessions[room] = None
                _stop[room] = False
                histories.pop(room, None)
                _summaries.pop(room, None)
                await ws.send_json({"type": "reset_ok"})

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        rooms[room] = [c for c in rooms.get(room, []) if c is not ws]


async def safe_send(ws: WebSocket, payload: dict) -> bool:
    try:
        # "shut up" mutes TTS centrally — drop voice lines but keep everything else flowing.
        if payload.get("type") == "tts" and _mute.get(getattr(ws, "_room", None)):
            return True
        await ws.send_json(payload)
        return True
    except Exception:
        return False


def _smart_ack(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("video", "generate video", "make a video", "create a video")):
        return "Starting your video. That takes a couple minutes. I'll notify you when it's ready."
    if any(w in t for w in ("runway", "runwayml")):
        return "Queuing your RunwayML generation. Give me about a minute."
    if any(w in t for w in ("image", "picture", "photo", "draw", "generate image")):
        return "Generating your image. Give me about ten seconds."
    if any(w in t for w in ("email", "send email", "write an email")):
        return "Drafting your email now."
    if any(w in t for w in ("slide", "presentation", "powerpoint", "pptx")):
        return "Building your presentation. Give me a few seconds."
    if any(w in t for w in ("search", "find", "look up", "research", "google")):
        return "Searching that now."
    if any(w in t for w in ("open", "launch", "start", "run")):
        return "On it."
    if any(w in t for w in ("click", "press", "type", "move", "drag")):
        return "Doing that now."
    if any(w in t for w in ("code", "write", "build", "create", "make", "generate")):
        return "Working on it. Give me a moment."
    if any(w in t for w in ("restaurant", "place", "eat", "food", "where", "recommend")):
        return "Let me find that for you."
    if any(w in t for w in ("what", "who", "when", "why", "how", "explain", "tell me", "?")):
        return "On it."
    if any(w in t for w in ("status", "what are you doing", "what's happening", "update")):
        return "Checking now."
    import random
    return random.choice(["On it.", "Got it.", "Right away."])


def _facts_context() -> str:
    """Compact block of live facts chatz can draw on to answer predefined questions."""
    from datetime import datetime
    now = datetime.now()
    h12 = now.hour % 12 or 12
    ampm = "AM" if now.hour < 12 else "PM"
    lines = [
        f"Current time: {h12}:{now.minute:02d} {ampm}.",
        f"Today: {_DAYS[now.weekday()]}, {_MONTHS[now.month-1]} {now.day}.",
    ]
    lf = _fast_facts
    pairs = [
        ("weather", "Beirut weather"),
        ("leb_restaurants", "Lebanon restaurants"),
        ("leb_activities", "Lebanon activities"),
        ("leb_safety", "Lebanon safe/unsafe regions"),
        ("leb_news", "Lebanon news"),
        ("schedule", "User's schedule"),
    ]
    for key, label in pairs:
        if lf.get(key):
            lines.append(f"{label}: {lf[key]}")
    return "\n".join(lines)


async def _chatz_front_door(text: str, ws: WebSocket, room: str) -> str:
    """chatz understands the user's actual intent, then either answers fast (using the
    predefined facts ONLY when the user truly asked about them) or signals that a real
    task is needed. Returns 'answered', 'claude', or 'empty'."""
    recap = _summaries.get(room, "")
    ctx = f"Recent conversation: {recap}\n" if recap else ""
    facts = _facts_context()
    prompt = (
        "You are MAX, a warm, fast voice assistant for Gabriel in Lebanon. "
        "Understand what the user actually means BEFORE you respond.\n\n"
        "RULES:\n"
        "1. If the user wants a real task done with tools — generate an image or video, send an email "
        "or telegram, search the web, control the PC, open or click things, write code or files, build "
        "a presentation, set a reminder, anything that needs an action — reply with EXACTLY this token "
        "and nothing else: NEEDS_CLAUDE\n"
        "2. Otherwise (small talk, a question, a comment) reply naturally in two or three spoken "
        "sentences. No markdown, no lists, no symbols.\n"
        "3. Use a fact below ONLY if the user genuinely asked about that exact topic. Never volunteer "
        "Lebanon restaurants, activities, or tips unless they asked. A casual comment gets a casual "
        "reply — for example 'tomorrow is the AI competition' just gets an enthusiastic short reply, "
        "not a travel guide.\n\n"
        f"LIVE FACTS:\n{facts}\n\n"
        f"{ctx}User says: {text}"
    )
    reply = (await _chat_z(prompt, timeout=12)).strip()
    if not reply:
        return "empty"
    if "NEEDS_CLAUDE" in reply.upper() and len(reply) < 40:
        return "claude"

    await safe_send(ws, {"type": "event", "data": {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": reply}]},
    }})
    clean = _clean_for_tts(reply)
    off = 0
    for m in SENT_RE.finditer(clean + " "):
        s = m.group(1).strip()
        if len(s) > 3:
            await safe_send(ws, {"type": "tts", "text": s})
            off = m.end()
    tail = clean[off:].strip()
    if tail and len(tail) > 3:
        await safe_send(ws, {"type": "tts", "text": tail})

    entry = f"User: {text[:90]} → MAX: {clean[:130]}"
    existing = _summaries.get(room, "")
    parts = [e for e in existing.split(" | ") if e][-1:] + [entry]
    _summaries[room] = " | ".join(parts)

    await safe_send(ws, {"type": "done", "session_id": None})
    return "answered"


async def run_fast_chat(text: str, ws: WebSocket, room: str) -> bool:
    """Track 1 fast responder via free chat-z LLM. Returns True if it answered."""
    recap = _summaries.get(room, "")
    ctx = f"[Recent context: {recap}]\n\n" if recap else ""
    prompt = (
        "You are MAX, a warm, fast, friendly voice assistant for someone in Lebanon. "
        "Reply in natural spoken sentences. No markdown, no lists, no symbols. "
        "Keep it short, two or three sentences, conversational.\n\n"
        f"{ctx}User says: {text}"
    )
    reply = await _chat_z(prompt, timeout=18)
    if not reply:
        return False

    # Send to UI + speak sentence by sentence
    await safe_send(ws, {"type": "event", "data": {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": reply}]},
    }})
    clean = _clean_for_tts(reply)
    off = 0
    for m in SENT_RE.finditer(clean + " "):
        s = m.group(1).strip()
        if len(s) > 3:
            await safe_send(ws, {"type": "tts", "text": s})
            off = m.end()
    tail = clean[off:].strip()
    if tail and len(tail) > 3:
        await safe_send(ws, {"type": "tts", "text": tail})

    # Sync so Claude has context
    entry = f"User: {text[:90]} → MAX: {clean[:130]}"
    existing = _summaries.get(room, "")
    parts = [e for e in existing.split(" | ") if e][-1:] + [entry]
    _summaries[room] = " | ".join(parts)

    await safe_send(ws, {"type": "done", "session_id": None})
    return True


async def run_msg(text: str, ws: WebSocket, room: str):
    if _stop.get(room):
        return  # room is stopped, ignore

    # ── INSTANT ACTION — open/play/launch via direct shell, zero LLM, flash ──
    action = _try_instant_action(text)
    if action:
        cmd, reply = action
        await safe_send(ws, {"type": "ack", "text": reply})
        # YouTube "play": resolve the first video and open its watch page (it auto-plays).
        if cmd.startswith("__yt_play__:"):
            q = cmd[len("__yt_play__:"):]
            watch = await _youtube_first_watch(q)
            cmd = f'start chrome "{watch}"'
        await safe_send(ws, {"type": "event", "data": {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": reply}]},
        }})
        await _exec_bash(cmd, timeout=10, room=room)
        await safe_send(ws, {"type": "done", "session_id": None})
        return

    # ── STATUS QUERY — report on running/recent tasks, don't start a new one ──
    if _is_status_query(text):
        report = _task_status_report(room)
        if report:
            await safe_send(ws, {"type": "event", "data": {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": report}]},
            }})
            await safe_send(ws, {"type": "tts", "text": report})
            await safe_send(ws, {"type": "done", "session_id": None})
            return
        # No tasks → fall through (it's a real question)

    # ── UNDERSTAND FIRST ──
    # Real task (deterministic verb gate) → straight to Claude, the brain.
    # Otherwise chatz reads the actual intent: it answers small talk and questions
    # itself (surfacing predefined facts ONLY when truly asked), and can still punt
    # to Claude via NEEDS_CLAUDE. No more blind keyword matching on the answer side.
    if not _is_agentic(text):
        verdict = await _chatz_front_door(text, ws, room)
        if verdict == "answered":
            return
        # 'claude' or 'empty' → fall through to the brain

    ack = _smart_ack(text)
    await safe_send(ws, {"type": "ack", "text": ack})

    _active[room] = _active.get(room, 0) + 1
    try:
        # ── CLAUDE IS ALWAYS THE BRAIN. chat-z only fills the silence while Claude works. ──
        enhanced = (
            f"{text}\n\n"
            f"[SCREEN_CONTEXT: data/last_screen.jpg has the current screen state]"
        )
        tid = _reg_add(room, text[:80])
        started = time.time()
        # chat-z bridge: if Claude hasn't responded in a few seconds, chat-z talks to fill the gap.
        filler = asyncio.create_task(_task_filler(ws, room, task_desc=text, delay=5.0))
        try:
            sid = sessions.get(room)
            new_sid = await run_claude(enhanced, sid, ws, room)
            if new_sid:
                sessions[room] = new_sid
            elapsed = int(time.time() - started)
            _reg_done(tid)
            _registry[tid]["result"] = f"took about {elapsed} seconds"
            # Feed result to chat-z context so it stays in sync with Claude
            entry = f"Done: {text[:80]} (in {elapsed}s)"
            existing = _summaries.get(room, "")
            parts = [e for e in existing.split(" | ") if e][-1:] + [entry]
            _summaries[room] = " | ".join(parts)
        except Exception:
            _reg_done(tid, "failed")
            raise
        finally:
            filler.cancel()
    finally:
        _active[room] = max(0, _active.get(room, 1) - 1)
        if _active.get(room, 0) == 0:
            asyncio.get_event_loop().run_in_executor(None, _kill_stray_pythons)


async def run_fast_llm(text: str, ws: WebSocket, room: str):
    """Direct LLM call — no claude subprocess, first token < 1s.
    Tries 3 endpoints in order; falls back to claude agent if all fail."""
    import httpx, uuid as _uuid
    from datetime import datetime, timezone as _tz

    MAX_SYS = (
        "You are MAX, a concise, direct AI assistant. No markdown, no bullet points. "
        "Natural spoken sentences only. Keep answers short."
    )

    async def _stream_openai() -> str:
        """OpenAI-compatible streaming (LLM_URL)."""
        payload = {
            "model": LLM_MODEL,
            "messages": [{"role": "system", "content": MAX_SYS}, {"role": "user", "content": text}],
            "stream": True, "max_tokens": 500,
        }
        full = ""
        tts_off = 0
        last_ui_len = 0   # throttle: only push UI update every 80 chars
        async with httpx.AsyncClient(timeout=20) as c:
            async with c.stream("POST", f"{LLM_URL}/chat/completions", json=payload) as r:
                if r.status_code not in (200, 201):
                    raise RuntimeError(f"status {r.status_code}")
                async for line in r.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        delta = json.loads(raw)["choices"][0]["delta"].get("content", "")
                    except Exception:
                        continue
                    if not delta:
                        continue
                    full += delta
                    # Only push a UI update every 80 chars to avoid flooding the WebSocket
                    if len(full) - last_ui_len >= 80:
                        last_ui_len = len(full)
                        await safe_send(ws, {"type": "event", "data": {
                            "type": "assistant",
                            "message": {"content": [{"type": "text", "text": full}]},
                        }})
                    # TTS: still sentence-driven (natural speech chunks)
                    new_part = _clean_for_tts(full)[tts_off:]
                    found = list(SENT_RE.finditer(new_part))
                    for m in found:
                        s = m.group(1).strip()
                        if len(s) > 3:
                            await safe_send(ws, {"type": "tts", "text": s})
                    if found:
                        tts_off += found[-1].end()
        # Final UI flush
        await safe_send(ws, {"type": "event", "data": {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": full}]},
        }})
        remaining = _clean_for_tts(full)[tts_off:].strip()
        if remaining and len(remaining) > 3:
            await safe_send(ws, {"type": "tts", "text": remaining})
        return full

    async def _stream_unlimitedai() -> str:
        """UnlimitedAI free streaming (no key, delta format)."""
        cid = str(_uuid.uuid4()); did = str(_uuid.uuid4())
        uid = str(_uuid.uuid4()); aid = str(_uuid.uuid4())
        now = datetime.now(_tz.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload = {
            "chatId": cid,
            "messages": [
                {"id": uid, "role": "user", "content": text,
                 "parts": [{"type": "text", "text": text}], "createdAt": now},
                {"id": aid, "role": "assistant", "content": "",
                 "parts": [{"type": "text", "text": ""}], "createdAt": now},
            ],
            "selectedChatModel": "chat-model-reasoning",
            "selectedCharacter": None, "selectedStory": None,
            "deviceId": did, "locale": "en",
        }
        headers = {
            "accept": "*/*", "content-type": "application/json",
            "referer": "https://app.unlimitedai.chat/", "x-next-intl-locale": "en",
        }
        full = ""
        tts_off = 0
        last_ui_len = 0
        async with httpx.AsyncClient(timeout=30) as c:
            async with c.stream("POST", "https://app.unlimitedai.chat/api/chat",
                                headers=headers, json=payload) as r:
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        delta = obj.get("delta", "") if obj.get("type") == "delta" else ""
                    except Exception:
                        continue
                    if not delta:
                        continue
                    full += delta
                    if len(full) - last_ui_len >= 80:
                        last_ui_len = len(full)
                        await safe_send(ws, {"type": "event", "data": {
                            "type": "assistant",
                            "message": {"content": [{"type": "text", "text": full}]},
                        }})
                    new_part = _clean_for_tts(full)[tts_off:]
                    found = list(SENT_RE.finditer(new_part))
                    for m in found:
                        s = m.group(1).strip()
                        if len(s) > 3:
                            await safe_send(ws, {"type": "tts", "text": s})
                    if found:
                        tts_off += found[-1].end()
        await safe_send(ws, {"type": "event", "data": {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": full}]},
        }})
        remaining = _clean_for_tts(full)[tts_off:].strip()
        if remaining and len(remaining) > 3:
            await safe_send(ws, {"type": "tts", "text": remaining})
        return full

    async def _call_glm() -> str:
        """GLM API (no stream, simple JSON)."""
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                "https://opus4-6.online/api/chat",
                json={"messages": [{"role": "system", "content": MAX_SYS},
                                   {"role": "user", "content": text}]},
                headers={"content-type": "application/json"},
            )
        content = r.json()["choices"][0]["message"]["content"]
        await safe_send(ws, {"type": "event", "data": {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": content}]},
        }})
        clean = _clean_for_tts(content)
        for m in SENT_RE.finditer(clean):
            s = m.group(1).strip()
            if len(s) > 3:
                await safe_send(ws, {"type": "tts", "text": s})
        return content

    result = ""
    for attempt in (_stream_openai, _stream_unlimitedai, _call_glm):
        try:
            result = await attempt()
            if result:
                break
        except Exception:
            continue

    if not result:
        # All fast paths failed — fall back to full claude agent
        sid = sessions.get(room)
        new_sid = await run_claude(text, sid, ws, room)
        if new_sid:
            sessions[room] = new_sid
        return

    await safe_send(ws, {"type": "done", "session_id": None})


async def run_api_claude(message: str, ws: WebSocket, room: str):
    """Call Anthropic API directly — no Node.js startup, first token ~300ms."""
    import httpx

    token = _get_api_token()
    if not token:
        # No token — fall back to CLI
        await run_claude(message, sessions.get(room), ws, room)
        return

    system = _get_system()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "anthropic-version": "2023-06-01",
    }

    # Rolling summary: keep a one-line recap of prior context + only last 2 messages
    summary = _summaries.get(room, "")
    hist = [{"role": "user", "content": message}]
    histories[room] = hist   # fresh every turn — summary carries the context

    tts_global_off = 0
    _retry_delay = 2

    for _turn in range(20):   # max 20 agentic steps
        if _stop.get(room):
            break

        # System = CLAUDE.md + compact session recap (no full history in system prompt)
        system_full = system
        if summary:
            system_full = f"{system}\n\n[SESSION RECAP: {summary}]"

        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 4096,
            "system": system_full,
            "messages": hist,
            "tools": [BASH_TOOL],
            "stream": True,
        }

        full_text = ""
        tool_calls: list[dict] = []
        cur_tc: Optional[dict] = None
        cur_tc_input = ""
        tts_off = 0
        last_ui = 0

        try:
            async with httpx.AsyncClient(timeout=120) as c:
                async with c.stream("POST", ANTHROPIC_API, headers=headers, json=payload) as r:
                    if r.status_code in (401, 403):
                        global _api_token
                        _api_token = None
                        body = (await r.aread()).decode(errors="replace")[:300]
                        raise RuntimeError(f"Auth failed ({r.status_code}): {body}")
                    if r.status_code in (429, 529):
                        await safe_send(ws, {"type": "tts", "text": "One moment, catching up."})
                        await asyncio.sleep(_retry_delay)
                        _retry_delay = min(_retry_delay * 2, 30)
                        break  # break inner, outer loop retries
                    if r.status_code != 200:
                        body = (await r.aread()).decode(errors="replace")[:300]
                        raise RuntimeError(f"API {r.status_code}: {body}")

                    async for line in r.aiter_lines():
                        if _stop.get(room):
                            break
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            ev = json.loads(raw)
                        except Exception:
                            continue
                        et = ev.get("type", "")

                        if et == "content_block_start":
                            blk = ev.get("content_block", {})
                            if blk.get("type") == "tool_use":
                                cur_tc = {"id": blk["id"], "name": blk["name"]}
                                cur_tc_input = ""

                        elif et == "content_block_delta":
                            d = ev.get("delta", {})
                            if d.get("type") == "text_delta":
                                chunk = d.get("text", "")
                                full_text += chunk
                                # Throttle UI updates
                                if len(full_text) - last_ui >= 60:
                                    last_ui = len(full_text)
                                    await safe_send(ws, {"type": "event", "data": {
                                        "type": "assistant",
                                        "message": {"content": [{"type": "text", "text": full_text}]},
                                    }})
                                # Sentence TTS
                                new_part = _clean_for_tts(full_text)[tts_off:]
                                found = list(SENT_RE.finditer(new_part))
                                for m in found:
                                    s = m.group(1).strip()
                                    if len(s) > 3:
                                        await safe_send(ws, {"type": "tts", "text": s})
                                if found:
                                    tts_off += found[-1].end()
                            elif d.get("type") == "input_json_delta" and cur_tc:
                                cur_tc_input += d.get("partial_json", "")

                        elif et == "content_block_stop":
                            if cur_tc:
                                try:
                                    cur_tc["input"] = json.loads(cur_tc_input) if cur_tc_input else {}
                                except Exception:
                                    cur_tc["input"] = {"command": cur_tc_input}
                                tool_calls.append(cur_tc)
                                cur_tc = None

        except Exception as e:
            err_str = str(e)
            # Show what actually failed
            await safe_send(ws, {"type": "event", "data": {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": f"[API error: {err_str[:200]}] — falling back to CLI"}]},
            }})
            # Fall back to the CLI subprocess
            _api_token = None  # force re-check next time
            sid = sessions.get(room)
            new_sid = await run_claude(message, sid, ws, room)
            if new_sid:
                sessions[room] = new_sid
            return

        # Flush final TTS
        remaining = _clean_for_tts(full_text)[tts_off:].strip()
        if remaining and len(remaining) > 3:
            await safe_send(ws, {"type": "tts", "text": remaining})

        # Final UI flush
        if full_text:
            await safe_send(ws, {"type": "event", "data": {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": full_text}]},
            }})

        # Append assistant turn to history
        asst_content: list = []
        if full_text:
            asst_content.append({"type": "text", "text": full_text})
        for tc in tool_calls:
            asst_content.append({"type": "tool_use", "id": tc["id"],
                                  "name": tc["name"], "input": tc["input"]})
        if asst_content:
            hist.append({"role": "assistant", "content": asst_content})

        if not tool_calls:
            break   # no more tools — done

        # Execute tools, show in UI, feed results back
        results = []
        for tc in tool_calls:
            cmd = tc["input"].get("command", "")
            tout = min(int(tc["input"].get("timeout", 60)), 120)
            await safe_send(ws, {"type": "event", "data": {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": "bash", "input": {"command": cmd[:120]}}]},
            }})
            out = await _exec_bash(cmd, timeout=tout, room=room) if cmd else "[no command]"
            results.append({"type": "tool_result", "tool_use_id": tc["id"], "content": out})

        hist.append({"role": "user", "content": results})

    # Kill every Python process this task spawned
    _kill_task_pids(room)

    # Update rolling summary so next turn has context without full history
    if full_text and len(full_text) > 20:
        # Build a compact one-liner: what the user asked + what MAX did
        user_req = message[:120].replace("\n", " ")
        result_snippet = _clean_for_tts(full_text)[:200].replace("\n", " ")
        new_entry = f"User: {user_req} → MAX: {result_snippet}"
        existing = _summaries.get(room, "")
        # Keep last 2 entries to limit growth
        entries = [e for e in existing.split(" | ") if e][-1:] + [new_entry]
        _summaries[room] = " | ".join(entries)

    await safe_send(ws, {"type": "done", "session_id": None})


async def broadcast(room: str, msg: dict, exclude: Optional[WebSocket] = None):
    for c in list(rooms.get(room, [])):
        if c is not exclude:
            try:
                await c.send_json(msg)
            except Exception:
                pass


def _clean_for_tts(text: str) -> str:
    t = PLAN_RE.sub("", text)
    t = re.sub(r"```[\s\S]*?```", "code block", t)
    t = re.sub(r"`[^`]+`", "", t)
    t = re.sub(r"https?://\S+", "link", t)
    t = re.sub(r"[*_#]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


async def run_claude(
    message: str,
    session_id: Optional[str],
    ws: WebSocket,
    room: Optional[str],
) -> Optional[str]:
    cmd = [
        CLAUDE_BIN, "-p", message,
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
    ]
    if session_id:
        cmd += ["--resume", session_id]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(MAX_DIR),
    )

    # Track proc so the stop command can terminate it
    if room:
        _procs.setdefault(room, []).append(proc)
        # Update the registry entry for this room with the real PID
        for t in _registry.values():
            if t["room"] == room and t["status"] == "running" and not t.get("pid"):
                t["pid"] = proc.pid
                break

    new_session_id = session_id
    last_text = ""
    tts_offset = 0

    async for raw in proc.stdout:
        # Check stop flag mid-stream
        if room and _stop.get(room):
            try:
                proc.terminate()
            except Exception:
                pass
            await safe_send(ws, {"type": "notification", "text": "Task stopped."})
            return new_session_id

        line = raw.decode(errors="replace").strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = evt.get("type", "")

        if etype == "result":
            new_session_id = evt.get("session_id") or new_session_id

        elif etype == "assistant":
            for block in evt.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    last_text = text

                    for m in PLAN_RE.finditer(text):
                        try:
                            plan = json.loads(m.group(1))
                            plan_evt = {"type": "plan_proposal", "plan": plan}
                            if not await safe_send(ws, plan_evt):
                                return new_session_id
                            if room:
                                await broadcast(room, plan_evt, exclude=ws)
                        except Exception:
                            pass

                    display = PLAN_RE.sub("", text).strip()
                    if display:
                        evt["message"]["content"] = [b for b in evt["message"]["content"] if b.get("type") != "text"]
                        evt["message"]["content"].append({"type": "text", "text": display})

                    # Streaming TTS: speak complete sentences as they arrive
                    clean = _clean_for_tts(text)
                    new_part = clean[tts_offset:]
                    found = list(SENT_RE.finditer(new_part))
                    for m in found:
                        sent = m.group(1).strip()
                        if len(sent) > 3:
                            if not await safe_send(ws, {"type": "tts", "text": sent}):
                                return new_session_id
                    if found:
                        tts_offset += found[-1].end()

        payload = {"type": "event", "data": evt}
        if not await safe_send(ws, payload):
            return new_session_id
        if room:
            await broadcast(room, payload, exclude=ws)

    await proc.wait()

    # Remove from tracked procs
    if room and proc in _procs.get(room, []):
        _procs[room].remove(proc)

    if last_text:
        clean = _clean_for_tts(last_text)
        remaining = clean[tts_offset:].strip()
        if remaining and len(remaining) > 3:
            await safe_send(ws, {"type": "tts", "text": remaining})

        if INPUT_RE.search(last_text):
            payload = {
                "type": "input_required",
                "prompt": last_text,
                "input_type": _detect_input_type(last_text),
            }
            await safe_send(ws, payload)
            if room:
                await broadcast(room, payload, exclude=ws)

    await safe_send(ws, {"type": "done", "session_id": new_session_id})
    return new_session_id


def _detect_input_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("password", "secret", "passphrase")):
        return "password"
    if any(w in t for w in ("otp", "2fa", "pin", "verification code", "auth code", "6-digit", "6 digit", "one-time")):
        return "otp"
    return "text"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="warning")
