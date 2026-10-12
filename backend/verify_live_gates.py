import urllib.request
import urllib.error
import json

BASE = "http://127.0.0.1:8000"

def test_live_auth_suite():
    # 1. Health check is public (HTTP 200)
    req = urllib.request.Request(f"{BASE}/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.getcode() == 200, f"Expected 200 on /health, got {resp.getcode()}"
        data = json.loads(resp.read().decode())
        assert data["status"] in ("ok", "degraded")
        print("[PASS] [PUBLIC] /health is accessible without authentication (HTTP 200)")

    # 2. Chat endpoint without token (HTTP 401)
    chat_payload = json.dumps({"messages": [{"role": "user", "content": "hi"}], "stream": False}).encode()
    req = urllib.request.Request(f"{BASE}/api/chat", data=chat_payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req)
        assert False, "Should have raised HTTPError 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print("[PASS] [GATE] /api/chat rejects missing token with HTTP 401")

    # 3. Chat endpoint with malformed/invalid token (HTTP 401)
    req = urllib.request.Request(f"{BASE}/api/chat", data=chat_payload, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer fake.invalid.jwt"
    })
    try:
        urllib.request.urlopen(req)
        assert False, "Should have raised HTTPError 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print("[PASS] [GATE] /api/chat rejects invalid token with HTTP 401")

    # 4. Conversations endpoint without token (HTTP 401)
    req = urllib.request.Request(f"{BASE}/api/conversations")
    try:
        urllib.request.urlopen(req)
        assert False, "Should have raised HTTPError 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print("[PASS] [GATE] /api/conversations rejects missing token with HTTP 401")

    # 5. /api/auth/me without token (HTTP 401)
    req = urllib.request.Request(f"{BASE}/api/auth/me")
    try:
        urllib.request.urlopen(req)
        assert False, "Should have raised HTTPError 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print("[PASS] [GATE] /api/auth/me rejects missing token with HTTP 401")

    print("\nAll live security gate assertions PASSED!")

if __name__ == "__main__":
    test_live_auth_suite()
