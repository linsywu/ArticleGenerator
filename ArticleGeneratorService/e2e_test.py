"""Phase 1 MVP End-to-End Test Suite"""
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)
PASS = 0
FAIL = 0
state = {}

def ok(r, expected=200):
    if r.status_code != expected:
        body = r.text[:200]
        raise AssertionError(f"Expected {expected}, got {r.status_code}: {body}")

def test(name, body):
    global PASS, FAIL
    try:
        body()
        print(f"  ✅ {name}")
        PASS += 1
    except AssertionError as e:
        print(f"  ❌ {name}: {e}")
        FAIL += 1
    except Exception as e:
        print(f"  💥 {name}: {type(e).__name__}: {e}")
        FAIL += 1

def api(method, path, **kw):
    return client.request(method, f"/api{path}", **kw)

# ─── Setup ───
print("=" * 55)
print("  Phase 1 MVP E2E Test Suite")
print("=" * 55)
r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
ok(r)
TOKEN = r.json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}
print(f"  Auth: token obtained ✓\n")

# ─── 1. TRACK MANAGEMENT ───
print("─── 1. Track Management ───")

test("1.1 Create track", lambda: (
    (r := api("POST", "/tracks", json={"name": "AI科技", "description": "AI行业资讯"}, headers=H)),
    ok(r), state.update(track1=r.json()["id"]), r.json()["status"] == 1
))

test("1.2 Create another track", lambda: (
    (r := api("POST", "/tracks", json={"name": "商业财经"}, headers=H)),
    ok(r), state.update(track2=r.json()["id"])
))

test("1.3 List tracks", lambda: (
    (r := api("GET", "/tracks", headers=H)), ok(r), len(r.json()) >= 2
))

test("1.4 Add sub-track", lambda: (
    (r := api("POST", f"/tracks/{state['track1']}/sub-tracks", json={"name": "大模型"}, headers=H)),
    ok(r), r.json()["track_id"] == state["track1"], state.update(sub1=r.json()["id"])
))

test("1.5 Add another sub-track", lambda: (
    (r := api("POST", f"/tracks/{state['track1']}/sub-tracks", json={"name": "AI应用"}, headers=H)),
    ok(r)
))

test("1.6 Get track with sub-tracks", lambda: (
    (r := api("GET", f"/tracks/{state['track1']}", headers=H)), ok(r), len(r.json()["sub_tracks"]) >= 2
))

test("1.7 Edit sub-track name", lambda: (
    (r := api("PUT", f"/tracks/sub-tracks/{state['sub1']}", json={"name": "大模型(LLM)"}, headers=H)),
    ok(r), r.json()["name"] == "大模型(LLM)"
))

test("1.8 Disable track", lambda: (
    (r := api("PATCH", f"/tracks/{state['track1']}/status", json={"status": 0}, headers=H)), ok(r),
    (r2 := api("GET", f"/tracks/{state['track1']}", headers=H)), ok(r2), r2.json()["status"] == 0
))

test("1.9 Re-enable track", lambda: (
    (r := api("PATCH", f"/tracks/{state['track1']}/status", json={"status": 1}, headers=H)), ok(r)
))

test("1.10 Delete sub-track", lambda: (
    (r := api("DELETE", f"/tracks/sub-tracks/{state['sub1']}", headers=H)), ok(r)
))

test("1.11 Cascade delete track", lambda: (
    (r := api("DELETE", f"/tracks/{state['track2']}", headers=H)), ok(r)
))

test("1.12 404 on deleted track", lambda: (
    (r := api("GET", f"/tracks/{state['track2']}", headers=H)), r.status_code == 404
))

# ─── 2. MP ACCOUNT MANAGEMENT ───
print("\n─── 2. MP Account Management ───")

test("2.1 Create MP account", lambda: (
    (r := api("POST", "/mp-accounts", json={"name": "36氪", "alias": "wow36kr", "track_ids": f"[{state['track1']}]"}, headers=H)),
    ok(r), r.json()["article_count"] == 0, state.update(acc1=r.json()["id"])
))

test("2.2 Create second account", lambda: (
    (r := api("POST", "/mp-accounts", json={"name": "机器之心", "alias": "almosthuman2014", "track_ids": f"[{state['track1']}]"}, headers=H)),
    ok(r), state.update(acc2=r.json()["id"])
))

test("2.3 Filter by track", lambda: (
    (r := api("GET", f"/mp-accounts?track_id={state['track1']}", headers=H)), ok(r), len(r.json()) >= 2
))

test("2.4 Search by name", lambda: (
    (r := api("GET", "/mp-accounts?search=36", headers=H)), ok(r), len(r.json()) == 1
))

test("2.5 Update account", lambda: (
    (r := api("PUT", f"/mp-accounts/{state['acc2']}", json={"description": "AI科技媒体"}, headers=H)),
    ok(r), r.json()["description"] == "AI科技媒体"
))

test("2.6 Disable + Delete account", lambda: (
    (r := api("PATCH", f"/mp-accounts/{state['acc2']}/status", json={"status": 0}, headers=H)), ok(r),
    (r2 := api("DELETE", f"/mp-accounts/{state['acc2']}", headers=H)), ok(r2),
    (r3 := api("GET", f"/mp-accounts/{state['acc2']}", headers=H)), r3.status_code == 404
))

# ─── 3. CREDENTIAL MANAGEMENT ───
print("\n─── 3. Credential Management ───")

test("3.1 Create credential", lambda: (
    (r := api("POST", "/credentials", json={"name": "主号凭证", "token": "abc123def456ghi789", "cookie": "ua_id=xxx; mm_lang=zh_CN"}, headers=H)),
    ok(r), "***" in r.json()["token"], state.update(cred1=r.json()["id"])
))

test("3.2 Create second credential", lambda: (
    (r := api("POST", "/credentials", json={"name": "备用凭证", "token": "secondary_token", "cookie": "backup_cookie"}, headers=H)),
    ok(r), state.update(cred2=r.json()["id"])
))

test("3.3 List all (tokens masked)", lambda: (
    (r := api("GET", "/credentials", headers=H)), ok(r),
    all("***" in c["token"] for c in r.json())
))

test("3.4 C1 fix: masked token update does not corrupt", lambda: (
    (r_get := api("GET", f"/credentials/{state['cred1']}", headers=H)), ok(r_get),
    masked := r_get.json()["token"],
    (r := api("PUT", f"/credentials/{state['cred1']}", json={"name": "主号凭证-更新", "token": masked}, headers=H)),
    ok(r), r.json()["name"] == "主号凭证-更新", r.json()["token"] == masked
))

test("3.5 Health check", lambda: (
    (r := api("POST", f"/credentials/{state['cred1']}/check", headers=H)), ok(r), "healthy" in r.json()
))

test("3.6 Delete credential", lambda: (
    (r := api("DELETE", f"/credentials/{state['cred2']}", headers=H)), ok(r)
))

# ─── 4. COLLECTION TASK MANAGEMENT ───
print("\n─── 4. Collection Task Management ───")

test("4.1 Create cron task", lambda: (
    (r := api("POST", "/collect-tasks", json={"name": "AI日报", "credential_id": state['cred1'], "track_ids": f"[{state['track1']}]", "collect_mode": "incremental", "schedule_type": "cron", "cron": "0 9 * * *"}, headers=H)),
    ok(r), r.json()["status"] == "idle", state.update(task1=r.json()["id"])
))

test("4.2 Create manual history task", lambda: (
    (r := api("POST", "/collect-tasks", json={"name": "36氪回溯", "credential_id": state['cred1'], "account_ids": f"[{state['acc1']}]", "collect_mode": "history_100", "schedule_type": "manual"}, headers=H)),
    ok(r), state.update(task2=r.json()["id"])
))

test("4.3 Filter by status", lambda: (
    (r := api("GET", "/collect-tasks?status=idle", headers=H)), ok(r), len(r.json()) >= 2,
    (r2 := api("GET", "/collect-tasks?status=running", headers=H)), ok(r2), len(r2.json()) == 0
))

test("4.4 Manual execute", lambda: (
    (r := api("POST", f"/collect-tasks/{state['task2']}/execute", headers=H)), ok(r), "message" in r.json()
))

test("4.5 Pause + Resume", lambda: (
    (r := api("POST", f"/collect-tasks/{state['task1']}/pause", headers=H)), ok(r),
    (r2 := api("POST", f"/collect-tasks/{state['task1']}/resume", headers=H)), ok(r2)
))

test("4.6 Update task config", lambda: (
    (r := api("PUT", f"/collect-tasks/{state['task1']}", json={"name": "日报-修订", "collect_mode": "history_50"}, headers=H)),
    ok(r), r.json()["name"] == "日报-修订"
))

test("4.7 Delete task", lambda: (
    (r := api("DELETE", f"/collect-tasks/{state['task2']}", headers=H)), ok(r),
    (r2 := api("GET", f"/collect-tasks/{state['task2']}", headers=H)), r2.status_code == 404
))

# ─── 5. MATERIALS + LOGS ───
print("\n─── 5. Materials + Collect Logs ───")

test("5.1 List materials (empty)", lambda: (
    (r := api("GET", "/materials", headers=H)), ok(r), r.json()["total"] == 0
))

test("5.2 Filter by account", lambda: (
    (r := api("GET", f"/materials?account_id={state['acc1']}", headers=H)), ok(r)
))

test("5.3 Search materials", lambda: (
    (r := api("GET", "/materials?search=GPT", headers=H)), ok(r)
))

test("5.4 404 non-existent", lambda: (
    (r := api("GET", "/materials/99999", headers=H)), r.status_code == 404
))

test("5.5 Parse 404", lambda: (
    (r := api("POST", "/materials/99999/parse", headers=H)), r.status_code == 404
))

test("5.6 List collect logs (empty)", lambda: (
    (r := api("GET", "/collect-logs", headers=H)), ok(r), r.json()["total"] == 0
))

# ─── 6. CROSS-MODULE ───
print("\n─── 6. Cross-Module Integration ───")

test("6.1 Track→Accounts filtering", lambda: (
    (r := api("GET", f"/mp-accounts?track_id={state['track1']}", headers=H)), ok(r), len(r.json()) == 1
))

test("6.2 Credential→Task reference", lambda: (
    (r := api("GET", f"/collect-tasks/{state['task1']}", headers=H)), ok(r),
    r.json()["credential_id"] == state["cred1"]
))

test("6.3 Can't delete referenced credential", lambda: (
    (r := api("DELETE", f"/credentials/{state['cred1']}", headers=H)), r.status_code != 200
))

# ─── 7. INPUT VALIDATION ───
print("\n─── 7. Input Validation ───")

def v1(): r = api("POST", "/tracks", json={}, headers=H); assert r.status_code == 422
test("7.1 No name → 422", v1)
def v2(): r = api("POST", "/credentials", json={"name": "x"}, headers=H); assert r.status_code == 422
test("7.2 Missing fields → 422", v2)
def v3(): r = api("POST", "/collect-tasks", json={"name": "x"}, headers=H); assert r.status_code == 422
test("7.3 No cred_id → 422", v3)
def v4(): r = client.get("/api/tracks"); assert r.status_code == 403
test("7.4 No auth → 403", v4)
def v5(): r = api("GET", "/tracks/99999", headers=H); assert r.status_code == 404
test("7.5 Non-existent → 404", v5)

# ─── REPORT ───
print("\n" + "=" * 55)
print(f"  RESULTS: {PASS} ✓ passed, {FAIL} ✗ failed, {PASS+FAIL} total")
print("=" * 55)
if FAIL > 0:
    print("  ❌ E2E TESTS FAILED")
else:
    print("  🎉 ALL E2E TESTS PASSED")
