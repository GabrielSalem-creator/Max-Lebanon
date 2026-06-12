# MAX Lebanon 🇱🇧
### *Maximize Your Life — The Voice AI Built for Lebanon*

> **Core mission:** Let Lebanese drivers keep their eyes on the road by giving them a voice-first AI that handles information, navigation, messaging, and tasks — without touching a phone.

---

## The Problem

Lebanon has one of the highest rates of road accidents per capita in the region. A leading cause: **distracted driving**. Drivers look at phones to check WhatsApp, search for routes, read news, find fuel prices. Every glance away from the road is a risk.

MAX removes that risk entirely. **You speak. MAX acts. Your eyes never leave the road.**

---

## Live URLs

| | URL | Purpose |
|---|---|---|
| 🔒 | [max.vdo-x.art](https://max.vdo-x.art) | The MAX app — password-protected |
| 🌍 | [max-lebanon.vdo-x.art](https://max-lebanon.vdo-x.art) | Public landing page — always online |

---

## How MAX Keeps Drivers Safe

### Fully hands-free — no screen, no touch
Say `MAX` to wake it. Speak your request. Hear the answer. That's the entire interaction — no buttons, no scrolling, no glancing down.

### Real-time road intelligence
- **Traffic** — *"Is there traffic on the highway to Beirut?"* → MAX pulls live congestion data and tells you the clearest route
- **Security alerts** — tracks incidents across Lebanon via LiveUAMap; warns you of danger zones before you drive into them
- **Safe route advice** — cross-references current conditions and recommends the safest road

### Replaces every dangerous phone habit
| Instead of... | Just say... |
|---|---|
| Opening WhatsApp while driving | *"MAX, send a WhatsApp to Dad saying I'm on my way"* |
| Searching for a song | *"MAX, play [song] on YouTube"* |
| Checking fuel prices at the pump | *"MAX, what's the fuel price today?"* |
| Reading news headlines | *"MAX, what's happening in Lebanon today?"* |
| Checking your calendar | *"MAX, what do I have tomorrow?"* |

---

## Full Feature Set

### ⚡ Instant skills (predefined — zero AI reasoning time)
These are hardcoded fast-paths. MAX already knows exactly how to do them:

| Command | Action |
|---|---|
| Play [song] on YouTube | Fetches the first video and opens it directly — auto-plays |
| Send WhatsApp to [contact] | Opens WhatsApp Web, finds the chat, sends |
| Fuel price today | Scrapes dgo.gov.lb, reads back LBP rates for 95/98/diesel |
| Traffic to [place] | Live congestion data, safest route |
| Security near me | LiveUAMap Lebanon — explosion/incident alerts |
| Summer 2026 events | Byblos, Beiteddine, Baalbeck, Wael Kfoury, Elissa concerts |
| My schedule | Reads your calendar aloud |
| Add [event] to calendar | Adds it, confirms by voice |
| Make a PowerPoint about [topic] | Generates slides, sends to Telegram or email |
| Generate an image of [thing] | AI image, delivered to Telegram |
| News in Lebanon | Live scraped headlines, read aloud |
| Restaurants near me | Options with opening hours and phone numbers |
| Lebanon safe regions | Which areas to avoid right now |

### 🧠 Trajectory memory — gets faster with every use
- **First time** doing a task: MAX works it out from scratch. It says *"I haven't done this before, give me a moment."*
- **Every time after**: MAX recognises the task, replays its proven recipe, adapts only the changed variables. **Milliseconds instead of minutes.**
- Tasks are saved as reusable recipes in a local cache. The more you use MAX, the faster it gets.

### 🌍 Three languages — auto-detected
MAX listens and speaks in whichever language you use:
- **English** — `en-US-JennyNeural`
- **French** — `fr-FR-DeniseNeural` *(auto-detected from French words)*
- **Lebanese Arabic** — `ar-LB-LaylaNeural` *(auto-detected from Arabic script)*

Switch mid-session — MAX keeps up.

### 🔒 Security
- `max.vdo-x.art` is password-protected — nobody can join and spam the AI
- Session token stored in browser localStorage — enter password once, stay logged in
- Passwords for third-party websites are **never** passed to the AI — injected directly into the browser DOM
- All credentials stay on your machine, never in the AI's context

### 🖥️ PC performance isolation
When MAX starts, it terminates all non-essential background processes to free RAM and CPU — keeping only Chrome and system essentials.

---

## Architecture

```
User voice/text
      │
      ▼
  Browser (index.html)
  ├── Wake word "MAX" → STT (EN/FR/AR, Web Speech API)
  ├── Browser-native TTS — zero latency
  ├── "Shut up" → mutes voice only, task keeps running
  └── WebSocket → server
              │
              ▼
  FastAPI server — main.py (port 8000)
  │
  ├─ Layer 1: Instant actions (0ms)
  │   YouTube play, open sites, Windows apps
  │
  ├─ Layer 2: Instant facts (0ms)
  │   Time, date, weather, Lebanese cached data (refreshed hourly)
  │
  ├─ Layer 3: Trajectory cache
  │   Known task → replay proven recipe with adapted variables
  │
  ├─ Layer 4: chat-z LLM (fast fill, ~1s)
  │   Conversation while Claude works in background
  │
  └─ Layer 5: Claude CLI (the brain)
      Real tasks: search, create, send, control PC
              │
              ├── tools.py
              │   search · images · video · email · telegram · PowerPoint
              │
              └── Windows PC control
                  Tier 1: Shell commands (fastest)
                  Tier 2: UIAutomation (structural)
                  Tier 3: OCR + pyautogui (visual fallback)

Cloudflare Tunnel
├── max.vdo-x.art          → localhost:8000  (protected app)
└── max-lebanon.vdo-x.art  → localhost:8001  (public landing page)

GitHub Pages (always online, PC-independent)
└── gabrielsalem-creator.github.io/Max-Lebanon/
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, asyncio |
| AI brain | Claude CLI (Anthropic) |
| Fast responder | chat-z (fills silence while Claude works) |
| TTS | Browser `speechSynthesis` + edge-tts |
| STT | Web Speech API (Chrome/Edge, multilingual) |
| PC control | Shell → UIAutomation → pyautogui |
| Images | Custom generation API |
| Video | RunwayML Gen-4 Turbo |
| Email | Resend API |
| Messaging | Telegram Bot API |
| Presentations | python-pptx |
| Tunnel | Cloudflare Tunnel |
| Landing page | GitHub Pages |
| Waitlist | Discord Webhook |

---

## Setup

### Requirements
```bash
pip install fastapi uvicorn httpx websockets pyautogui edge-tts python-dotenv python-pptx
```
Claude Code CLI must be installed and authenticated.

### Environment (`.env` — never committed)
```env
RESEND_KEY=your_resend_api_key
TG_TOKEN=your_telegram_bot_token
VID_KEY=your_video_api_key
IMG_URL=https://image-z.created.app/api/generate-image
LLM_URL=https://chat.good.hidns.vip/api/openai/v1
USER_EMAIL=your@email.com
RUNWAY_JWT=your_runwayml_jwt
```

### Run
```bash
# Terminal 1 — main app
python main.py

# Terminal 2 — landing page server
python landing_server.py

# Terminal 3 — Cloudflare tunnel
cloudflared tunnel run max
```

### Cloudflare config (`~/.cloudflared/config.yml`)
```yaml
tunnel: <your-tunnel-id>
credentials-file: ~/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: max.vdo-x.art
    service: http://localhost:8000
  - hostname: max-lebanon.vdo-x.art
    service: http://localhost:8001
  - service: http_status:404
```

---

## Voice Quick Reference

```
Wake word: "MAX"

ROAD SAFETY
  "Is there traffic to Jounieh?"
  "Any danger zones near Beirut?"
  "Which road is safest right now?"
  "Any explosions in the south?"

INFORMATION
  "What's the fuel price today?"
  "What's the news in Lebanon?"
  "What are the summer 2026 events?"
  "What time is it?" / "What's the weather?"

CALENDAR
  "What's on my schedule today?"
  "Add Byblos festival July 5th to my calendar"

MEDIA
  "Play Fairuz on YouTube"
  "Shut up" — stops voice, task keeps running
  "Stop everything" — cancels all tasks

MESSAGES
  "Send a WhatsApp to [name] saying [message]"
  "Send an email to [address] about [topic]"

CREATE
  "Generate an image of [thing] and send to Telegram"
  "Make a PowerPoint about [topic] and email it"

LEBANON
  "Are the southern regions safe?"
  "Good restaurants in Hamra with hours?"
  "Cool things to do in Beirut this summer?"
```

---

## Project Status

| Feature | Status |
|---|---|
| Voice assistant (EN / FR / AR) | ✅ Live |
| Password-protected app | ✅ Live |
| Session persistence | ✅ Live |
| Trajectory memory | ✅ Live |
| Instant fast-path skills | ✅ Live |
| Image & video generation | ✅ Live |
| PowerPoint generation | ✅ Live |
| Email & Telegram delivery | ✅ Live |
| Landing page (GitHub Pages) | ✅ Live |
| Discord waitlist webhook | ✅ Live |
| Cloudflare tunnel (both domains) | ✅ Live |
| Mic self-hearing guard | ✅ Live |
| "Shut up" mute (task keeps running) | ✅ Live |
| WhatsApp automation | 🔄 In progress |
| Google Calendar API | 🔄 In progress |
| LiveUAMap real-time tracking | 🔄 In progress |
| Live fuel price scraping (dgo.gov.lb) | 🔄 In progress |
| Live traffic data | 🔄 In progress |

---

## Why Lebanon

Lebanon has specific challenges that generic AI assistants ignore:
- Roads that require real-time security awareness
- Fuel prices that change daily in LBP
- A population that switches between Arabic, French, and English mid-sentence
- Local events, restaurants, and regions that no global dataset covers

MAX is built around those realities. It is not a global product with a Lebanese flag — it is a tool designed from the ground up for how life works here.

**Goal: measurably reduce distracted-driving accidents in Lebanon by making voice-first AI the default way people interact with information while on the road.**

---

*Built in Lebanon 🇱🇧 · [max-lebanon.vdo-x.art](https://max-lebanon.vdo-x.art) · Maximize your life.*
