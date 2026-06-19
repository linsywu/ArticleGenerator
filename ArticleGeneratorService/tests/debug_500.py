"""Debug 500 errors on running backend"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.environ["DATABASE_URL"] = "sqlite:///./article_generator.db"

from app.main import app
from fastapi.testclient import TestClient
import traceback

# Use TestClient which doesn't require a running server
c = TestClient(app)

# Login
r = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

for path in [
    "/api/articles?status=pending_review",
    "/api/tasks/unified",
    "/api/generate/tasks/list",
    "/api/scenario-configs",
]:
    print(f"\n=== {path} ===")
    try:
        r = c.get(path, headers=h)
        print(f"Status: {r.status_code}")
        if r.status_code >= 400:
            print(f"Body: {r.text[:500]}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        traceback.print_exc()
