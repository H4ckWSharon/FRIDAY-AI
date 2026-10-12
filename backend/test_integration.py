"""
FRIDAY AI -- Integration Test Suite
"""
import asyncio, json, sys
import httpx
import pytest

pytestmark = pytest.mark.integration

BASE = "http://127.0.0.1:8000"
results = []

def report(name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}]  {name}" + (f"\n         {detail}" if detail else ""))
    results.append((name, ok))

def test_config():
    sys.path.insert(0, ".")
    from config import get_settings
    s = get_settings()
    ok = (s.ollama_base_url == "http://127.0.0.1:11435" and "Huihui-Qwen3-Coder-30B" in s.ollama_model)
    report("Config loading", ok, f"url={s.ollama_base_url}")

async def test_health():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE}/health")
        d = r.json()
        ok = r.status_code == 200 and d.get("status") == "ok" and d.get("ollama_reachable")
        report("GET /health", ok, f"status={d.get('status')} model_tail={d.get('model','')[-25:]}")

async def test_chat_nonstream():
    body = {"messages": [{"role": "user", "content": "Say FRIDAY_OK only."}], "stream": False}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{BASE}/api/chat", json=body)
        d = r.json()
        ok = r.status_code == 200 and bool(d.get("content","").strip())
        report("POST /api/chat non-stream", ok, d.get("content","")[:80])

async def test_chat_stream():
    body = {"messages": [{"role": "user", "content": "What is XSS? One sentence."}], "stream": True}
    chunks, done = 0, False
    text = ""
    async with httpx.AsyncClient(timeout=120) as c:
        async with c.stream("POST", f"{BASE}/api/chat", json=body) as r:
            if r.status_code != 200:
                report("POST /api/chat stream", False, f"HTTP {r.status_code}"); return
            buf = ""
            async for raw in r.aiter_bytes():
                buf += raw.decode("utf-8", errors="replace")
                parts = buf.split("\n\n"); buf = parts.pop()
                for part in parts:
                    ev, da = None, None
                    for line in part.splitlines():
                        if line.startswith("event:"): ev = line.split(":",1)[1].strip()
                        if line.startswith("data:"):  da = line.split(":",1)[1].strip()
                    if not da: continue
                    try: payload = json.loads(da)
                    except: continue
                    if ev == "chunk": chunks += 1; text += payload.get("text","")
                    elif ev == "done": done = True
    ok = chunks > 0 and done
    report("POST /api/chat stream (SSE)", ok, f"chunks={chunks} done={done} preview: {text[:80]}")

async def test_empty():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/api/chat", json={"messages": [], "stream": False})
        report("Empty messages rejected 422", r.status_code == 422, f"HTTP {r.status_code}")

def test_frontend():
    with open("../index.html", encoding="utf-8", errors="replace") as f: html = f.read()
    ok = "http://127.0.0.1:8000" in html and "/api/chat" in html and "stream: true" in html
    report("Frontend endpoint config", ok)

async def main():
    print("\n" + "="*55)
    print("  FRIDAY AI Integration Tests")
    print("="*55)
    test_config()
    await test_health()
    await test_chat_nonstream()
    await test_chat_stream()
    await test_empty()
    test_frontend()
    passed = sum(1 for _, ok in results if ok)
    print(f"\n  Results: {passed}/{len(results)} tests passed")
    print("="*55 + "\n")
if __name__ == "__main__":
    asyncio.run(main())
