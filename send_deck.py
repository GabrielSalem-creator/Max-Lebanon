# -*- coding: utf-8 -*-
import os, base64, json, urllib.request
from pathlib import Path

# load .env like tools.py does
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

RESEND_KEY = os.environ["RESEND_KEY"]
TO = os.environ.get("USER_EMAIL", "gsal4066@gmail.com")
PPTX = r"C:\Users\Admin\OneDrive\Documents\max\data\Stock_Market_Investing_Guide.pptx"

content_b64 = base64.b64encode(Path(PPTX).read_bytes()).decode()

html = """
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:600px;margin:auto;color:#0B1F3A">
  <div style="background:#0B1F3A;padding:28px 30px;border-top:6px solid #E8B54B;border-radius:10px 10px 0 0">
    <h1 style="color:#fff;margin:0;font-size:24px">The Stock Market — Investing the Smart Way</h1>
    <p style="color:#B8C4D4;margin:8px 0 0">Your personal investing guide is attached.</p>
  </div>
  <div style="background:#f5f7fa;padding:26px 30px;border-radius:0 0 10px 10px">
    <p>Hi Gabriel,</p>
    <p>Here's your presentation on the stock market and how to invest the smart way. It's an 11-slide deck with custom visuals covering:</p>
    <ul style="line-height:1.7">
      <li>What the stock market is and why to invest</li>
      <li>The core building blocks — stocks, bonds, index funds & ETFs</li>
      <li>The power of compounding (with real numbers)</li>
      <li>Risk, diversification & asset allocation by age</li>
      <li>Smart strategies, common mistakes, and a step-by-step starter plan</li>
    </ul>
    <p style="font-size:13px;color:#667">Educational content only — not personalized financial advice.</p>
    <p style="margin-top:22px">— MAX</p>
  </div>
</div>
"""

payload = {
    "from": "MAX <onboarding@resend.dev>",
    "to": [TO],
    "subject": "Your Stock Market Investing Guide (Presentation)",
    "html": html,
    "attachments": [{
        "filename": "Stock_Market_Investing_Guide.pptx",
        "content": content_b64,
    }],
}

import httpx
r = httpx.post(
    "https://api.resend.com/emails",
    headers={"Authorization": f"Bearer {RESEND_KEY}"},
    json=payload,
    timeout=60,
)
print("STATUS", r.status_code, r.text[:300])
if r.status_code in (200, 201):
    print("SENT_TO", TO)
