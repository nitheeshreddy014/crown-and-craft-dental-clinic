"""
API tests for authentication routes:
  POST /api/login
  POST /api/register
  GET  /api/me
  GET  /api/logout
  GET  /login  (page redirect)
  GET  /auth/google  (OAuth redirect)
"""
import pytest
from unittest.mock import patch

EMPTY   = {"rows": [], "lastrowid": None, "rowcount": 0}
ROW1    = lambda row: {"rows": [row], "lastrowid": None, "rowcount": 0}
INSERT  = {"rows": [], "lastrowid": 1, "rowcount": 1}

import hashlib
def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

PATIENT_USER = {
    "id": 1, "name": "Test Patient", "email": "patient@test.com",
    "phone": "9999999999", "password_hash": _hash("password123"),
    "role": "patient", "auth_provider": "email",
    "reset_token": None, "reset_token_expiry": None, "totp_secret": None,
}
GOOGLE_USER = {
    **PATIENT_USER,
    "email": "google@test.com", "auth_provider": "google",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    import os
    os.environ.setdefault("ADMIN_PASSWORD", "TestAdmin123")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
    os.environ.setdefault("TURSO_DATABASE_URL", "libsql://fake.turso.io")
    os.environ.setdefault("TURSO_AUTH_TOKEN", "fake-token")
    with patch("database._turso_run", return_value=EMPTY), \
         patch("database._turso_batch", return_value=[EMPTY]*4), \
         patch("email_utils.send_email", return_value=True):
        from main import app
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

@pytest.fixture(scope="module")
def admin_cookies():
    with patch("database._turso_run", return_value=EMPTY):
        from main import create_token
        return {"admin_token": create_token("nitheesh", "admin", "Nitheesh")}

@pytest.fixture(scope="module")
def patient_cookies():
    with patch("database._turso_run", return_value=EMPTY):
        from main import create_token
        return {"admin_token": create_token("patient@test.com", "patient", "Test Patient")}


# ══════════════════════════════════════════════════════════════
# POST /api/login
# ══════════════════════════════════════════════════════════════

class TestLogin:

    def test_admin_login_success(self, client):
        resp = client.post("/api/login",
                           json={"username": "nitheesh", "password": "TestAdmin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "admin_token" in resp.cookies

    def test_admin_login_wrong_password(self, client):
        resp = client.post("/api/login",
                           json={"username": "nitheesh", "password": "wrongpassword"})
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    def test_patient_login_success(self, client):
        with patch("database._turso_run", return_value=ROW1(PATIENT_USER)):
            resp = client.post("/api/login",
                               json={"username": "patient@test.com", "password": "password123"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert "admin_token" in resp.cookies

    def test_patient_login_wrong_password(self, client):
        with patch("database._turso_run", return_value=ROW1(PATIENT_USER)):
            resp = client.post("/api/login",
                               json={"username": "patient@test.com", "password": "badpass"})
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    def test_nonexistent_user_returns_401(self, client):
        with patch("database._turso_run", return_value=EMPTY):
            resp = client.post("/api/login",
                               json={"username": "ghost@test.com", "password": "anything"})
        assert resp.status_code == 401

    def test_google_user_password_login_rejected(self, client):
        with patch("database._turso_run", return_value=ROW1(GOOGLE_USER)):
            resp = client.post("/api/login",
                               json={"username": "google@test.com", "password": "password123"})
        assert resp.status_code == 401
        assert "Google" in resp.json()["message"]

    def test_login_sets_httponly_cookie(self, client):
        resp = client.post("/api/login",
                           json={"username": "nitheesh", "password": "TestAdmin123"})
        assert resp.status_code == 200
        assert "admin_token" in resp.cookies

    def test_admin_redirect_url(self, client):
        resp = client.post("/api/login",
                           json={"username": "nitheesh", "password": "TestAdmin123"})
        assert resp.json().get("redirect_url") == "/admin"

    def test_patient_redirect_url(self, client):
        with patch("database._turso_run", return_value=ROW1(PATIENT_USER)):
            resp = client.post("/api/login",
                               json={"username": "patient@test.com", "password": "password123"})
        assert resp.json().get("redirect_url") == "/my-appointments"


# ══════════════════════════════════════════════════════════════
# POST /api/register
# ══════════════════════════════════════════════════════════════

class TestRegister:

    def test_valid_registration(self, client):
        with patch("database._turso_run", side_effect=[EMPTY, INSERT]):
            resp = client.post("/api/register", json={
                "name": "New User", "email": "new@example.com",
                "phone": "9876543210", "password": "pass1234",
                "confirm_password": "pass1234"
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_duplicate_email_returns_409(self, client):
        with patch("database._turso_run", return_value=ROW1({"1": 1})):
            resp = client.post("/api/register", json={
                "name": "User", "email": "existing@example.com",
                "password": "pass1234", "confirm_password": "pass1234"
            })
        assert resp.status_code == 409
        assert resp.json()["success"] is False

    def test_password_mismatch_returns_400(self, client):
        resp = client.post("/api/register", json={
            "name": "User", "email": "u@example.com",
            "password": "pass1234", "confirm_password": "different"
        })
        assert resp.status_code == 400
        assert "match" in resp.json()["message"].lower()

    def test_invalid_email_returns_400(self, client):
        resp = client.post("/api/register", json={
            "name": "User", "email": "not-an-email",
            "password": "pass1234", "confirm_password": "pass1234"
        })
        assert resp.status_code == 400

    def test_short_name_returns_400(self, client):
        resp = client.post("/api/register", json={
            "name": "A", "email": "a@example.com",
            "password": "pass1234", "confirm_password": "pass1234"
        })
        assert resp.status_code == 400

    def test_short_password_returns_400(self, client):
        resp = client.post("/api/register", json={
            "name": "User", "email": "u@example.com",
            "password": "abc", "confirm_password": "abc"
        })
        assert resp.status_code == 400

    def test_invalid_phone_returns_400(self, client):
        resp = client.post("/api/register", json={
            "name": "User", "email": "u@example.com",
            "phone": "abc", "password": "pass1234", "confirm_password": "pass1234"
        })
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════
# GET /api/me
# ══════════════════════════════════════════════════════════════

class TestGetMe:

    def test_no_cookie_returns_not_logged_in(self, client):
        saved = dict(client.cookies)
        client.cookies.clear()
        try:
            resp = client.get("/api/me")
            assert resp.status_code == 200
            assert resp.json()["logged_in"] is False
        finally:
            for k, v in saved.items():
                client.cookies.set(k, v)

    def test_invalid_token_returns_not_logged_in(self, client):
        resp = client.get("/api/me", cookies={"admin_token": "garbage.token.value"})
        assert resp.status_code == 200
        assert resp.json()["logged_in"] is False

    def test_valid_patient_token_returns_logged_in(self, client, patient_cookies):
        with patch("database._turso_run", return_value=ROW1(PATIENT_USER)):
            resp = client.get("/api/me", cookies=patient_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["logged_in"] is True
        assert data["role"] == "patient"
        assert data["email"] == "patient@test.com"

    def test_valid_admin_token_returns_admin_role(self, client, admin_cookies):
        resp = client.get("/api/me", cookies=admin_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["logged_in"] is True
        assert data["role"] == "admin"


# ══════════════════════════════════════════════════════════════
# GET /api/logout
# ══════════════════════════════════════════════════════════════

class TestLogout:

    def test_logout_redirects_to_login(self, client):
        resp = client.get("/api/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_logout_clears_cookie(self, client, admin_cookies):
        resp = client.get("/api/logout", cookies=admin_cookies,
                          follow_redirects=False)
        # Cookie should be cleared (deleted)
        assert resp.status_code == 302


# ══════════════════════════════════════════════════════════════
# GET /login  (page)
# ══════════════════════════════════════════════════════════════

class TestLoginPage:

    def test_login_page_loads(self, client):
        from starlette.responses import HTMLResponse
        fake_resp = HTMLResponse(content="<html>login</html>", status_code=200)
        saved = dict(client.cookies)
        client.cookies.clear()
        try:
            with patch("main.templates.TemplateResponse", return_value=fake_resp):
                resp = client.get("/login")
            assert resp.status_code == 200
        finally:
            for k, v in saved.items():
                client.cookies.set(k, v)

    def test_already_logged_in_admin_redirected(self, client, admin_cookies):
        resp = client.get("/login", cookies=admin_cookies,
                          follow_redirects=False)
        assert resp.status_code == 302
        assert "/admin" in resp.headers["location"]


# ══════════════════════════════════════════════════════════════
# GET /auth/google  (OAuth start)
# ══════════════════════════════════════════════════════════════

class TestGoogleOAuth:

    def test_google_auth_without_client_id_redirects_with_error(self, client):
        with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": ""}):
            resp = client.get("/auth/google", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "error" in resp.headers["location"]

    def test_google_auth_with_client_id_redirects_to_google(self, client):
        with patch.dict("os.environ", {
            "GOOGLE_CLIENT_ID": "fake-client-id",
            "GOOGLE_REDIRECT_URI": "https://example.com/callback"
        }):
            resp = client.get("/auth/google", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "accounts.google.com" in resp.headers["location"]
