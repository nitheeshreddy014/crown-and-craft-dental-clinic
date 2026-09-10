"""
Integration tests for the full authentication flow:
  Register → Login → Use API → Logout → Confirm logged out
"""
import pytest, hashlib
from unittest.mock import patch

EMPTY  = {"rows": [], "lastrowid": None, "rowcount": 0}
INSERT = {"rows": [], "lastrowid": 1,    "rowcount": 1}

def _row(r): return {"rows": [r], "lastrowid": None, "rowcount": 0}
def _hash(p): return hashlib.sha256(p.encode()).hexdigest()

NEW_USER = {
    "id": 1, "name": "Integration User", "email": "integ@test.com",
    "phone": "9876543210", "password_hash": _hash("integpass1"),
    "role": "patient", "auth_provider": "email",
    "reset_token": None, "reset_token_expiry": None, "totp_secret": None,
}


@pytest.fixture(scope="module")
def client():
    import os
    os.environ.setdefault("ADMIN_PASSWORD", "TestAdmin123")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
    os.environ.setdefault("TURSO_DATABASE_URL", "libsql://fake.turso.io")
    os.environ.setdefault("TURSO_AUTH_TOKEN", "fake-token")
    with patch("database._turso_run", return_value=EMPTY), \
         patch("database._turso_batch", return_value=[EMPTY] * 4), \
         patch("email_utils.send_email", return_value=True):
        from main import app
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ══════════════════════════════════════════════════════════════
# Flow 1: Register → Login → /api/me → Logout → not logged in
# ══════════════════════════════════════════════════════════════

class TestRegisterLoginLogout:

    def test_register_new_user(self, client):
        # email not yet taken → EMPTY, then INSERT
        with patch("database._turso_run", side_effect=[EMPTY, INSERT]):
            resp = client.post("/api/register", json={
                "name": "Integration User",
                "email": "integ@test.com",
                "phone": "9876543210",
                "password": "integpass1",
                "confirm_password": "integpass1"
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_login_after_register(self, client):
        with patch("database._turso_run", return_value=_row(NEW_USER)):
            resp = client.post("/api/login", json={
                "username": "integ@test.com",
                "password": "integpass1"
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert "admin_token" in resp.cookies

    def test_me_endpoint_after_login(self, client):
        with patch("database._turso_run", return_value=_row(NEW_USER)):
            login_resp = client.post("/api/login", json={
                "username": "integ@test.com",
                "password": "integpass1"
            })
        token = login_resp.cookies.get("admin_token")
        assert token is not None

        with patch("database._turso_run", return_value=_row(NEW_USER)):
            me_resp = client.get("/api/me",
                                 cookies={"admin_token": token})
        assert me_resp.json()["logged_in"] is True
        assert me_resp.json()["email"] == "integ@test.com"

    def test_logout_clears_session(self, client):
        with patch("database._turso_run", return_value=_row(NEW_USER)):
            login_resp = client.post("/api/login", json={
                "username": "integ@test.com",
                "password": "integpass1"
            })
        token = login_resp.cookies.get("admin_token")

        # Logout
        client.get("/api/logout", cookies={"admin_token": token},
                   follow_redirects=False)

        # After logout the token cookie is gone from client jar — /api/me should show logged out
        me_resp = client.get("/api/me")
        assert me_resp.json()["logged_in"] is False


# ══════════════════════════════════════════════════════════════
# Flow 2: Register duplicate email → rejected
# ══════════════════════════════════════════════════════════════

class TestDuplicateEmailRejected:

    def test_duplicate_register_returns_409(self, client):
        # Email already exists
        with patch("database._turso_run", return_value=_row({"1": 1})):
            resp = client.post("/api/register", json={
                "name": "Another User",
                "email": "integ@test.com",
                "password": "pass1234",
                "confirm_password": "pass1234"
            })
        assert resp.status_code == 409
        assert resp.json()["success"] is False


# ══════════════════════════════════════════════════════════════
# Flow 3: Admin login → access /admin → access analytics → logout
# ══════════════════════════════════════════════════════════════

class TestAdminFullFlow:

    def test_admin_login(self, client):
        resp = client.post("/api/login", json={
            "username": "nitheesh",
            "password": "TestAdmin123"
        })
        assert resp.status_code == 200
        assert resp.json()["redirect_url"] == "/admin"
        assert "admin_token" in resp.cookies

    def test_admin_accesses_dashboard(self, client):
        resp = client.post("/api/login",
                           json={"username": "nitheesh", "password": "TestAdmin123"})
        token = resp.cookies["admin_token"]

        analytics_result = [
            {"rows": [], "lastrowid": None, "rowcount": 0},
            {"rows": [], "lastrowid": None, "rowcount": 0},
            {"rows": [], "lastrowid": None, "rowcount": 0},
            {"rows": [{"cnt": 0}], "lastrowid": None, "rowcount": 0},
        ]
        from starlette.responses import HTMLResponse
        fake_resp = HTMLResponse(content="<html>admin</html>", status_code=200)
        with patch("main.get_appointments", return_value=[]), \
             patch("main.get_contact_messages", return_value=[]), \
             patch("main.get_slots", return_value=[]), \
             patch("main.get_user_by_email", return_value=None), \
             patch("main.templates.TemplateResponse", return_value=fake_resp):
            dash_resp = client.get("/admin", cookies={"admin_token": token})
        assert dash_resp.status_code == 200

    def test_admin_accesses_analytics(self, client):
        resp = client.post("/api/login",
                           json={"username": "nitheesh", "password": "TestAdmin123"})
        token = resp.cookies["admin_token"]

        analytics_result = [
            {"rows": [{"month": "2025-01", "count": 3}], "lastrowid": None, "rowcount": 0},
            {"rows": [{"service": "Cleaning", "count": 2}], "lastrowid": None, "rowcount": 0},
            {"rows": [{"status": "Pending", "count": 1}], "lastrowid": None, "rowcount": 0},
            {"rows": [{"cnt": 5}], "lastrowid": None, "rowcount": 0},
        ]
        with patch("database._turso_batch", return_value=analytics_result):
            analytics_resp = client.get("/api/admin/analytics",
                                        cookies={"admin_token": token})
        assert analytics_resp.status_code == 200
        assert analytics_resp.json()["total_patients"] == 5

    def test_admin_logout_blocks_dashboard(self, client):
        resp = client.post("/api/login",
                           json={"username": "nitheesh", "password": "TestAdmin123"})
        token = resp.cookies["admin_token"]

        client.get("/api/logout", cookies={"admin_token": token},
                   follow_redirects=False)

        # After logout — should redirect away from /admin
        blocked = client.get("/admin", follow_redirects=False)
        assert blocked.status_code == 302
        assert "/login" in blocked.headers["location"]
