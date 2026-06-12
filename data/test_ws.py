import asyncio, json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

async def test():
    import websockets
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "message", "text": "say exactly: MAX IS WORKING"}))
        for _ in range(40):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=4)
                d = json.loads(msg)
                t = d.get("type", "")
                if t == "tts":
                    print(f"ACK: {d.get('text','')}", flush=True)
                elif t == "event":
                    evt = d.get("data", {})
                    if evt.get("type") == "assistant":
                        for b in evt.get("message", {}).get("content", []):
                            if b.get("type") == "text":
                                print(f"TEXT: {b['text'][:200]}", flush=True)
                elif t == "done":
                    print(f"DONE. session={d.get('session_id','?')[:16]}", flush=True)
                    break
            except asyncio.TimeoutError:
                print("(timeout)", flush=True)
                break

asyncio.run(test())
