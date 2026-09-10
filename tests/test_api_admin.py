"""
API tests for admin-only routes:
  GET  /admin                                   — dashboard page
  POST /api/admin/appointments/{id}/status      — update status
  GET  /api/admin/analytics                     — analytics
  GET  /api/admin/slots                         — list slots
  POST /api/admin/slots                         — create slot
  DELETE /api/admin/slots/{id}                  — delete slot
  PATCH  /api/admin/slots/{id}                  — toggle slot
  POST /api/admin/2fa/setup                     — setup 2FA
  POST /api/admin/2fa/verify                    — verify 2FA
"""
import pytest
from unittest.mock import patch, MagicMock

EMPTY       = {"rows": [], "lastrowid": None, "rowcount": 0}
INSERT_OK   = {"rows": [], "lastrowid": 1,    "rowcount": 1}
UPDATE_OK   = {"rows": [], "lastrowid": None, "rowcount": 1}
UPDATE_FAIL = {"rows": [], "lastrowid": None, "rowcount": 0}

def _row(r):  return {"rows": [r],  "lastrowid": None, "rowcount": 0}
def _rows(l): return {"rows": l,    "lastrowid": None, "rowcount": 0}

SAMPLE_APT = {
    "id": 1, "name": "John", "phone": "9999999999",
    "email": "john@test.com", "preferred_date": "2025-12-01",
    "preferred_time": "10:00 AM", "service": "Cleaning",
    "message": "", "appointment_status": "Pending",
    "created_at": "2025-01-01 10:00:00",
}
SAMPLE_SLOT = {
    "id": 1, "slot_date": "2025-12-01", "slot_time": "10:00 AM",
    "is_available": 1, "created_at": "2025-01-01 10:00:00",
}
ADMIN_USER_ROW = {
    "id": 99, "name": "nitheesh", "email": "nitheesh@clinic.local",
    "phone": "", "password_hash": "x", "role": "admin",
    "auth_provider": "email", "reset_token": None,
    "reset_token_expiry": None, "totp_secret": "JBSWY3DPEHPK3PXP",
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
         patch("database._turso_batch", return_value=[EMPTY] * 4), \
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
        return {"admin_token": create_token("patient@test.com", "patient", "Patient")}


# ══════════════════════════════════════════════════════════════
# GET /admin — Dashboard page
# ══════════════════════════════════════════════════════════════

class TestAdminDashboard:

    def test_no_token_redirects_to_login(self, client):
        resp = client.get("/admin", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_patient_token_redirects_to_login(self, client, patient_cookies):
        resp = client.get("/admin", cookies=patient_cookies,
                          follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_admin_token_loads_dashboard(self, client, admin_cookies):
        from starlette.responses import HTMLResponse
        fake_resp = HTMLResponse(content="<html>admin</html>", status_code=200)
        with patch("main.get_appointments", return_value=[]), \
             patch("main.get_contact_messages", return_value=[]), \
             patch("main.get_slots", return_value=[]), \
             patch("main.get_user_by_email", return_value=None), \
             patch("main.templates.TemplateResponse", return_value=fake_resp):
            resp = client.get("/admin", cookies=admin_cookies)
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════
# POST /api/admin/appointments/{id}/status
# ══════════════════════════════════════════════════════════════

class TestUpdateAppointmentStatus:

    def test_no_auth_returns_401(self, client):
        resp = client.post("/api/admin/appointments/1/status",
                           json={"status": "Confirmed"})
        assert resp.status_code == 401

    def test_patient_auth_returns_401(self, client, patient_cookies):
        resp = client.post("/api/admin/appointments/1/status",
                           json={"status": "Confirmed"},
                           cookies=patient_cookies)
        assert resp.status_code == 401

    def test_valid_status_update(self, client, admin_cookies):
        with patch("database._turso_run", side_effect=[
            _row(SAMPLE_APT),  # get_appointment_by_id
            UPDATE_OK,         # update_appointment_status
        ]), patch("email_utils.send_email", return_value=True):
            resp = client.post("/api/admin/appointments/1/status",
                               json={"status": "Confirmed"},
                               cookies=admin_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.parametrize("status", ["Pending", "Confirmed", "Cancelled", "Completed"])
    def test_all_valid_statuses_accepted(self, client, admin_cookies, status):
        with patch("database._turso_run", side_effect=[
            _row(SAMPLE_APT), UPDATE_OK
        ]), patch("email_utils.send_email", return_value=True):
            resp = client.post("/api/admin/appointments/1/status",
                               json={"status": status},
                               cookies=admin_cookies)
        assert resp.status_code == 200

    def test_invalid_status_returns_400(self, client, admin_cookies):
        resp = client.post("/api/admin/appointments/1/status",
                           json={"status": "Flying"},
                           cookies=admin_cookies)
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_nonexistent_appointment_returns_404(self, client, admin_cookies):
        with patch("database._turso_run", side_effect=[
            _row(SAMPLE_APT), UPDATE_FAIL
        ]):
            resp = client.post("/api/admin/appointments/9999/status",
                               json={"status": "Confirmed"},
                               cookies=admin_cookies)
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════
# GET /api/admin/analytics
# ══════════════════════════════════════════════════════════════

class TestAdminAnalytics:

    def test_no_auth_returns_401(self, client):
        resp = client.get("/api/admin/analytics")
        assert resp.status_code == 401

    def test_patient_auth_returns_401(self, client, patient_cookies):
        resp = client.get("/api/admin/analytics", cookies=patient_cookies)
        assert resp.status_code == 401

    def test_admin_gets_analytics(self, client, admin_cookies):
        analytics_result = [
            {"rows": [{"month": "2025-01", "count": 5}], "lastrowid": None, "rowcount": 0},
            {"rows": [{"service": "Cleaning", "count": 3}], "lastrowid": None, "rowcount": 0},
            {"rows": [{"status": "Pending", "count": 2}], "lastrowid": None, "rowcount": 0},
            {"rows": [{"cnt": 10}], "lastrowid": None, "rowcount": 0},
        ]
        with patch("database._turso_batch", return_value=analytics_result):
            resp = client.get("/api/admin/analytics", cookies=admin_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "monthly" in data
        assert "by_service" in data
        assert "by_status" in data
        assert "total_patients" in data


# ══════════════════════════════════════════════════════════════
# Slot Management
# ══════════════════════════════════════════════════════════════

class TestSlotManagement:

    # GET /api/admin/slots
    def test_list_slots_no_auth_returns_401(self, client):
        resp = client.get("/api/admin/slots")
        assert resp.status_code == 401

    def test_list_slots_admin(self, client, admin_cookies):
        with patch("database._turso_run", return_value=_rows([SAMPLE_SLOT])):
            resp = client.get("/api/admin/slots", cookies=admin_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert len(resp.json()["slots"]) == 1

    def test_list_slots_with_date_filter(self, client, admin_cookies):
        with patch("database._turso_run", return_value=_rows([SAMPLE_SLOT])):
            resp = client.get("/api/admin/slots?date=2025-12-01",
                              cookies=admin_cookies)
        assert resp.status_code == 200

    # POST /api/admin/slots
    def test_create_slot_no_auth_returns_401(self, client):
        resp = client.post("/api/admin/slots",
                           json={"slot_date": "2025-12-01", "slot_time": "09:00 AM"})
        assert resp.status_code == 401

    def test_create_slot_success(self, client, admin_cookies):
        with patch("database._turso_run", return_value=INSERT_OK):
            resp = client.post("/api/admin/slots",
                               json={"slot_date": "2025-12-01", "slot_time": "09:00 AM"},
                               cookies=admin_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_create_duplicate_slot_returns_400(self, client, admin_cookies):
        with patch("main.add_slot", return_value=False):
            resp = client.post("/api/admin/slots",
                               json={"slot_date": "2025-12-01", "slot_time": "09:00 AM"},
                               cookies=admin_cookies)
        assert resp.status_code == 400

    def test_create_slot_empty_date_returns_422(self, client, admin_cookies):
        resp = client.post("/api/admin/slots",
                           json={"slot_date": "", "slot_time": "09:00 AM"},
                           cookies=admin_cookies)
        assert resp.status_code in (400, 422)

    # DELETE /api/admin/slots/{id}
    def test_delete_slot_no_auth_returns_401(self, client):
        resp = client.delete("/api/admin/slots/1")
        assert resp.status_code == 401

    def test_delete_slot_success(self, client, admin_cookies):
        with patch("database._turso_run", return_value=UPDATE_OK):
            resp = client.delete("/api/admin/slots/1", cookies=admin_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_nonexistent_slot_returns_404(self, client, admin_cookies):
        with patch("database._turso_run", return_value=UPDATE_FAIL):
            resp = client.delete("/api/admin/slots/9999", cookies=admin_cookies)
        assert resp.status_code == 404

    # PATCH /api/admin/slots/{id}
    def test_toggle_slot_no_auth_returns_401(self, client):
        resp = client.patch("/api/admin/slots/1",
                            json={"is_available": False})
        assert resp.status_code == 401

    def test_toggle_slot_success(self, client, admin_cookies):
        with patch("database._turso_run", return_value=UPDATE_OK):
            resp = client.patch("/api/admin/slots/1",
                                json={"is_available": False},
                                cookies=admin_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ══════════════════════════════════════════════════════════════
# 2FA — Setup & Verify
# ══════════════════════════════════════════════════════════════

class TestTwoFactorAuth:

    def test_setup_2fa_no_auth_returns_401(self, client):
        resp = client.post("/api/admin/2fa/setup")
        assert resp.status_code == 401

    def test_setup_2fa_admin_success(self, client, admin_cookies):
        mock_totp = MagicMock()
        mock_totp.provisioning_uri.return_value = "otpauth://totp/test"
        with patch("main.get_user_by_email", return_value=None), \
             patch("main.set_totp_secret", return_value=None), \
             patch("pyotp.random_base32", return_value="JBSWY3DPEHPK3PXP"), \
             patch("pyotp.TOTP", return_value=mock_totp):
            resp = client.post("/api/admin/2fa/setup", cookies=admin_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "secret" in data
        assert "uri" in data

    def test_verify_2fa_no_auth_returns_401(self, client):
        resp = client.post("/api/admin/2fa/verify", json={"code": "123456"})
        assert resp.status_code == 401

    def test_verify_2fa_valid_code(self, client, admin_cookies):
        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        with patch("main.get_user_by_email", return_value=ADMIN_USER_ROW), \
             patch("pyotp.TOTP", return_value=mock_totp):
            resp = client.post("/api/admin/2fa/verify",
                               json={"code": "123456"},
                               cookies=admin_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_verify_2fa_invalid_code(self, client, admin_cookies):
        mock_totp = MagicMock()
        mock_totp.verify.return_value = False
        with patch("main.get_user_by_email", return_value=ADMIN_USER_ROW), \
             patch("pyotp.TOTP", return_value=mock_totp):
            resp = client.post("/api/admin/2fa/verify",
                               json={"code": "000000"},
                               cookies=admin_cookies)
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_verify_2fa_not_setup_returns_400(self, client, admin_cookies):
        user_no_totp = {**ADMIN_USER_ROW, "totp_secret": None}
        with patch("main.get_user_by_email", return_value=user_no_totp):
            resp = client.post("/api/admin/2fa/verify",
                               json={"code": "123456"},
                               cookies=admin_cookies)
        assert resp.status_code == 400
        assert "not set up" in resp.json()["message"].lower()
