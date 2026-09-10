"""
API tests for miscellaneous routes:
  GET  /api/health
  POST /api/contact
  POST /api/forgot-password
  POST /api/reset-password
  PUT  /api/profile
  GET  /api/cron/reminders
  GET  /api/records
  POST /api/records
  DELETE /api/records/{id}
  GET  /blog
  GET  /blog/{slug}
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

EMPTY       = {"rows": [], "lastrowid": None, "rowcount": 0}
INSERT_OK   = {"rows": [], "lastrowid": 1,    "rowcount": 1}
UPDATE_OK   = {"rows": [], "lastrowid": None, "rowcount": 1}
UPDATE_FAIL = {"rows": [], "lastrowid": None, "rowcount": 0}

def _row(r):  return {"rows": [r],  "lastrowid": None, "rowcount": 0}
def _rows(l): return {"rows": l,    "lastrowid": None, "rowcount": 0}

import hashlib
def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

SAMPLE_USER = {
    "id": 1, "name": "Test Patient", "email": "patient@test.com",
    "phone": "9999999999", "password_hash": _hash("password123"),
    "role": "patient", "auth_provider": "email",
    "reset_token": "valid-reset-token",
    "reset_token_expiry": (datetime.utcnow() + timedelta(minutes=25)).isoformat(),
    "totp_secret": None,
}

EXPIRED_USER = {
    **SAMPLE_USER,
    "reset_token_expiry": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
}

SAMPLE_RECORD = {
    "id": 1, "user_email": "patient@test.com",
    "file_url": "https://example.com/xray.pdf",
    "file_name": "xray.pdf", "record_type": "X-Ray",
    "uploaded_at": "2025-01-01 10:00:00",
}

SAMPLE_BLOG_POST = {
    "id": 1, "title": "Test Post", "slug": "test-post",
    "summary": "A test summary", "content": "<p>Test content</p>",
    "author": "Dr. Maneesh", "published": 1,
    "created_at": "2025-01-01 10:00:00",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    import os
    os.environ.setdefault("ADMIN_PASSWORD", "TestAdmin123")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
    os.environ.setdefault("TURSO_DATABASE_URL", "libsql://fake.turso.io")
    os.environ.setdefault("TURSO_AUTH_TOKEN", "fake-token")
    os.environ.setdefault("CRON_SECRET", "test-cron-secret")
    with patch("database._turso_run", return_value=EMPTY), \
         patch("database._turso_batch", return_value=[EMPTY] * 4), \
         patch("email_utils.send_email", return_value=True):
        from main import app
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

@pytest.fixture(scope="module")
def patient_cookies():
    with patch("database._turso_run", return_value=EMPTY):
        from main import create_token
        return {"admin_token": create_token("patient@test.com", "patient", "Test Patient")}

@pytest.fixture(scope="module")
def admin_cookies():
    with patch("database._turso_run", return_value=EMPTY):
        from main import create_token
        return {"admin_token": create_token("nitheesh", "admin", "Nitheesh")}


# ══════════════════════════════════════════════════════════════
# GET /api/health
# ══════════════════════════════════════════════════════════════

class TestHealthCheck:

    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        resp = client.get("/api/health")
        assert resp.json()["status"] == "ok"

    def test_health_returns_clinic_name(self, client):
        resp = client.get("/api/health")
        assert "Crown" in resp.json()["clinic"]

    def test_health_returns_version(self, client):
        resp = client.get("/api/health")
        assert "version" in resp.json()

    def test_health_returns_timestamp(self, client):
        resp = client.get("/api/health")
        assert "timestamp" in resp.json()


# ══════════════════════════════════════════════════════════════
# POST /api/contact
# ══════════════════════════════════════════════════════════════

class TestContactForm:

    def test_valid_contact_returns_200(self, client):
        with patch("database._turso_run", return_value=INSERT_OK):
            resp = client.post("/api/contact", json={
                "name": "Jane Doe", "email": "jane@example.com",
                "message": "I have a question about services."
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_short_message_returns_422(self, client):
        resp = client.post("/api/contact", json={
            "name": "Jane", "email": "jane@example.com", "message": "Hi"
        })
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self, client):
        resp = client.post("/api/contact", json={
            "name": "Jane", "email": "not-an-email",
            "message": "I have a valid question here."
        })
        assert resp.status_code == 422

    def test_short_name_returns_422(self, client):
        resp = client.post("/api/contact", json={
            "name": "J", "email": "j@example.com",
            "message": "Valid question about services."
        })
        assert resp.status_code == 422

    def test_optional_phone_accepted(self, client):
        with patch("database._turso_run", return_value=INSERT_OK):
            resp = client.post("/api/contact", json={
                "name": "Jane", "email": "jane@example.com",
                "phone": "9999999999",
                "message": "I have a question about services."
            })
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════
# POST /api/forgot-password
# ══════════════════════════════════════════════════════════════

class TestForgotPassword:

    def test_registered_email_returns_success(self, client):
        with patch("database._turso_run", return_value=_row(SAMPLE_USER)), \
             patch("database.set_reset_token", return_value=None), \
             patch("email_utils.send_password_reset", return_value=True):
            resp = client.post("/api/forgot-password",
                               json={"email": "patient@test.com"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_unknown_email_also_returns_success(self, client):
        """Must NOT reveal whether email exists — always returns success."""
        with patch("database._turso_run", return_value=EMPTY):
            resp = client.post("/api/forgot-password",
                               json={"email": "ghost@nowhere.com"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_invalid_email_returns_400(self, client):
        resp = client.post("/api/forgot-password",
                           json={"email": "not-an-email"})
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════
# POST /api/reset-password
# ══════════════════════════════════════════════════════════════

class TestResetPassword:

    def test_valid_token_and_matching_passwords(self, client):
        with patch("database._turso_run", return_value=_row(SAMPLE_USER)), \
             patch("database.update_password", return_value=None), \
             patch("database.clear_reset_token", return_value=None):
            resp = client.post("/api/reset-password", json={
                "token": "valid-reset-token",
                "password": "newpassword1",
                "confirm_password": "newpassword1"
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_passwords_do_not_match_returns_400(self, client):
        resp = client.post("/api/reset-password", json={
            "token": "some-token",
            "password": "newpassword1",
            "confirm_password": "different123"
        })
        assert resp.status_code == 400
        assert "match" in resp.json()["message"].lower()

    def test_invalid_token_returns_400(self, client):
        with patch("database._turso_run", return_value=EMPTY):
            resp = client.post("/api/reset-password", json={
                "token": "bad-token",
                "password": "newpassword1",
                "confirm_password": "newpassword1"
            })
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_expired_token_returns_400(self, client):
        with patch("database._turso_run", return_value=_row(EXPIRED_USER)), \
             patch("database.clear_reset_token", return_value=None):
            resp = client.post("/api/reset-password", json={
                "token": "valid-reset-token",
                "password": "newpassword1",
                "confirm_password": "newpassword1"
            })
        assert resp.status_code == 400
        assert "expired" in resp.json()["message"].lower()

    def test_short_password_returns_400(self, client):
        resp = client.post("/api/reset-password", json={
            "token": "tok", "password": "abc", "confirm_password": "abc"
        })
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════
# PUT /api/profile
# ══════════════════════════════════════════════════════════════

class TestUpdateProfile:

    def test_unauthenticated_returns_401(self, client):
        resp = client.put("/api/profile",
                          json={"name": "New Name", "phone": "9999999999"})
        assert resp.status_code == 401

    def test_admin_token_returns_401(self, client, admin_cookies):
        resp = client.put("/api/profile",
                          json={"name": "New Name"},
                          cookies=admin_cookies)
        assert resp.status_code == 401

    def test_patient_can_update_profile(self, client, patient_cookies):
        with patch("database.update_user_profile", return_value=None):
            resp = client.put("/api/profile",
                              json={"name": "Updated Name", "phone": "8888888888"},
                              cookies=patient_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_updated_profile_re_issues_token(self, client, patient_cookies):
        with patch("database.update_user_profile", return_value=None):
            resp = client.put("/api/profile",
                              json={"name": "New Name"},
                              cookies=patient_cookies)
        assert resp.status_code == 200
        assert "admin_token" in resp.cookies

    def test_short_name_returns_400(self, client, patient_cookies):
        resp = client.put("/api/profile",
                          json={"name": "X"},
                          cookies=patient_cookies)
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════
# GET /api/cron/reminders
# ══════════════════════════════════════════════════════════════

class TestCronReminders:

    def test_correct_secret_returns_200(self, client):
        with patch("database._turso_run", return_value=EMPTY), \
             patch("email_utils.send_reminder", return_value=True):
            resp = client.get(
                "/api/cron/reminders",
                headers={"authorization": "Bearer test-cron-secret"}
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_wrong_secret_returns_401(self, client):
        resp = client.get(
            "/api/cron/reminders",
            headers={"authorization": "Bearer wrong-secret"}
        )
        assert resp.status_code == 401

    def test_no_auth_header_returns_401(self, client):
        resp = client.get("/api/cron/reminders")
        assert resp.status_code == 401

    def test_returns_reminders_sent_count(self, client):
        apt = {
            "id": 1, "email": "p@test.com", "name": "Patient",
            "preferred_date": "2025-12-02", "preferred_time": "10:00 AM",
            "service": "Cleaning"
        }
        with patch("database._turso_run", return_value=_rows([apt])), \
             patch("email_utils.send_reminder", return_value=True):
            resp = client.get(
                "/api/cron/reminders",
                headers={"authorization": "Bearer test-cron-secret"}
            )
        data = resp.json()
        assert "reminders_sent" in data
        assert "total" in data


# ══════════════════════════════════════════════════════════════
# Dental Records — GET / POST / DELETE /api/records
# ══════════════════════════════════════════════════════════════

class TestDentalRecords:

    def test_get_records_unauthenticated_returns_401(self, client):
        saved = dict(client.cookies)
        client.cookies.clear()
        try:
            resp = client.get("/api/records")
            assert resp.status_code == 401
        finally:
            for k, v in saved.items():
                client.cookies.set(k, v)

    def test_get_records_patient_returns_list(self, client, patient_cookies):
        with patch("database._turso_run", return_value=_rows([SAMPLE_RECORD])):
            resp = client.get("/api/records", cookies=patient_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert len(resp.json()["records"]) == 1

    def test_post_record_unauthenticated_returns_401(self, client):
        saved = dict(client.cookies)
        client.cookies.clear()
        try:
            resp = client.post("/api/records", json={
                "file_url": "https://example.com/xray.pdf",
                "file_name": "xray.pdf"
            })
            assert resp.status_code == 401
        finally:
            for k, v in saved.items():
                client.cookies.set(k, v)

    def test_post_record_patient_success(self, client, patient_cookies):
        with patch("database._turso_run", return_value=INSERT_OK):
            resp = client.post("/api/records",
                               json={
                                   "file_url": "https://example.com/xray.pdf",
                                   "file_name": "xray.pdf",
                                   "record_type": "X-Ray"
                               },
                               cookies=patient_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_record_unauthenticated_returns_401(self, client):
        saved = dict(client.cookies)
        client.cookies.clear()
        try:
            resp = client.delete("/api/records/1")
            assert resp.status_code == 401
        finally:
            for k, v in saved.items():
                client.cookies.set(k, v)

    def test_delete_own_record_success(self, client, patient_cookies):
        with patch("database._turso_run", return_value=UPDATE_OK):
            resp = client.delete("/api/records/1", cookies=patient_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_other_users_record_returns_404(self, client, patient_cookies):
        """SECURITY: must not delete another user's record."""
        with patch("database._turso_run", return_value=UPDATE_FAIL):
            resp = client.delete("/api/records/99", cookies=patient_cookies)
        assert resp.status_code == 404
        assert resp.json()["success"] is False


# ══════════════════════════════════════════════════════════════
# Blog routes
# ══════════════════════════════════════════════════════════════

class TestBlogRoutes:

    def test_blog_list_page_loads(self, client):
        from starlette.responses import HTMLResponse
        fake_resp = HTMLResponse(content="<html>blog</html>", status_code=200)
        with patch("main.get_blog_posts", return_value=[SAMPLE_BLOG_POST]), \
             patch("main.templates.TemplateResponse", return_value=fake_resp):
            resp = client.get("/blog")
        assert resp.status_code == 200

    def test_blog_post_valid_slug_loads(self, client):
        from starlette.responses import HTMLResponse
        fake_resp = HTMLResponse(content="<html>blog post</html>", status_code=200)
        with patch("main.get_blog_post", return_value=SAMPLE_BLOG_POST), \
             patch("main.get_blog_posts", return_value=[SAMPLE_BLOG_POST]), \
             patch("main.templates.TemplateResponse", return_value=fake_resp):
            resp = client.get("/blog/test-post")
        assert resp.status_code == 200

    def test_blog_post_invalid_slug_redirects(self, client):
        with patch("database.get_blog_post", return_value=None):
            resp = client.get("/blog/nonexistent-slug", follow_redirects=False)
        assert resp.status_code == 302
        assert "/blog" in resp.headers["location"]
