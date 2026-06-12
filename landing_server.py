"""Minimal landing page server for max-lebanon.vdo-x.art on port 8001."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
LANDING = Path(__file__).parent / "landing"

app.mount("/img", StaticFiles(directory=str(LANDING / "img")), name="img")

@app.get("/")
async def root():
    return HTMLResponse((LANDING / "index.html").read_text(encoding="utf-8"))

@app.get("/{path:path}")
async def catch_all(path: str):
    return HTMLResponse((LANDING / "index.html").read_text(encoding="utf-8"))

if __name__ == "__main__":
    uvicorn.run("landing_server:app", host="0.0.0.0", port=8001, reload=False, log_level="warning")
