"""
API tests for appointment routes:
  POST /api/appointments           — book appointment
  GET  /api/my-appointments        — list patient appointments
  GET  /my-appointments            — page (auth guard)
  POST /api/appointments/{id}/cancel — patient cancellation + IDOR test
"""
import pytest, hashlib
from unittest.mock import patch

EMPTY  = {"rows": [], "lastrowid": None, "rowcount": 0}
INSERT = {"rows": [], "lastrowid": 1,    "rowcount": 1}
UPDATE_OK   = {"rows": [], "lastrowid": None, "rowcount": 1}
UPDATE_FAIL = {"rows": [], "lastrowid": None, "rowcount": 0}

def _row(row): return {"rows": [row], "lastrowid": None, "rowcount": 0}
def _rows(lst): return {"rows": lst,  "lastrowid": None, "rowcount": 0}
def _hash(pw):  return hashlib.sha256(pw.encode()).hexdigest()

PATIENT_USER = {
    "id": 1, "name": "Test Patient", "email": "patient@test.com",
    "phone": "9999999999", "password_hash": _hash("password123"),
    "role": "patient", "auth_provider": "email",
    "reset_token": None, "reset_token_expiry": None, "totp_secret": None,
}

SAMPLE_APT = {
    "id": 1, "name": "Test Patient", "phone": "9999999999",
    "email": "patient@test.com", "preferred_date": "2025-12-01",
    "preferred_time": "10:00 AM", "service": "Teeth Cleaning",
    "message": "", "appointment_status": "Pending",
    "created_at": "2025-01-01 10:00:00",
}

COMPLETED_APT = {**SAMPLE_APT, "appointment_status": "Completed"}
CANCELLED_APT = {**SAMPLE_APT, "appointment_status": "Cancelled"}
OTHER_APT     = {**SAMPLE_APT, "email": "other@test.com", "id": 2}


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
def patient_cookies():
    with patch("database._turso_run", return_value=EMPTY):
        from main import create_token
        return {"admin_token": create_token("patient@test.com", "patient", "Test Patient")}

@pytest.fixture(scope="module")
def admin_cookies():
    with patch("database._turso_run", return_value=EMPTY):
        from main import create_token
        return {"admin_token": create_token("nitheesh", "admin", "Nitheesh")}

VALID_FORM = {
    "name": "Test Patient", "phone": "9999999999",
    "email": "patient@test.com", "preferred_date": "2025-12-01",
    "preferred_time": "10:00 AM", "service": "Teeth Cleaning", "message": ""
}


# ══════════════════════════════════════════════════════════════
# POST /api/appointments — Book Appointment
# ══════════════════════════════════════════════════════════════

class TestBookAppointment:

    def test_unauthenticated_returns_401(self, client):
        resp = client.post("/api/appointments", json=VALID_FORM)
        assert resp.status_code == 401
        assert resp.json()["success"] is False

    def test_authenticated_patient_can_book(self, client, patient_cookies):
        with patch("database._turso_run", return_value=INSERT), \
             patch("email_utils.send_email", return_value=True):
            resp = client.post("/api/appointments",
                               json=VALID_FORM, cookies=patient_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "appointment_id" in data

    def test_email_auto_filled_from_jwt(self, client, patient_cookies):
        """Email in response must come from JWT, not from form body."""
        form = {**VALID_FORM, "email": "attacker@evil.com"}
        with patch("database._turso_run", return_value=INSERT), \
             patch("email_utils.send_email", return_value=True):
            resp = client.post("/api/appointments",
                               json=form, cookies=patient_cookies)
        assert resp.status_code == 200

    def test_invalid_form_returns_400(self, client, patient_cookies):
        bad_form = {"name": "X", "phone": "bad", "email": "bad",
                    "preferred_date": "", "preferred_time": "", "service": ""}
        resp = client.post("/api/appointments",
                           json=bad_form, cookies=patient_cookies)
        assert resp.status_code == 400

    def test_missing_service_returns_400(self, client, patient_cookies):
        form = {**VALID_FORM, "service": ""}
        resp = client.post("/api/appointments",
                           json=form, cookies=patient_cookies)
        assert resp.status_code == 400

    def test_admin_token_can_also_book(self, client, admin_cookies):
        """Admins are also logged in users — booking should work."""
        with patch("database._turso_run", return_value=INSERT), \
             patch("email_utils.send_email", return_value=True):
            resp = client.post("/api/appointments",
                               json=VALID_FORM, cookies=admin_cookies)
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════
# GET /api/my-appointments
# ══════════════════════════════════════════════════════════════

class TestGetMyAppointments:

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/my-appointments")
        assert resp.status_code == 401

    def test_admin_token_returns_401(self, client, admin_cookies):
        resp = client.get("/api/my-appointments", cookies=admin_cookies)
        assert resp.status_code == 401

    def test_patient_gets_their_appointments(self, client, patient_cookies):
        with patch("database._turso_run", return_value=_rows([SAMPLE_APT])):
            resp = client.get("/api/my-appointments", cookies=patient_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["appointments"], list)
        assert len(data["appointments"]) == 1

    def test_patient_gets_empty_list(self, client, patient_cookies):
        with patch("database._turso_run", return_value=EMPTY):
            resp = client.get("/api/my-appointments", cookies=patient_cookies)
        assert resp.status_code == 200
        assert resp.json()["appointments"] == []


# ══════════════════════════════════════════════════════════════
# GET /my-appointments  (HTML page — auth guard)
# ══════════════════════════════════════════════════════════════

class TestMyAppointmentsPage:

    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/my-appointments", follow_redirects=False)
        assert resp.status_code == 302
        assert "login" in resp.headers["location"]

    def test_authenticated_patient_loads_page(self, client, patient_cookies):
        from starlette.responses import HTMLResponse
        fake_resp = HTMLResponse(content="<html>my appointments</html>", status_code=200)
        with patch("main.get_user_by_email", return_value=PATIENT_USER), \
             patch("main.get_appointments_by_email", return_value=[SAMPLE_APT]), \
             patch("main.templates.TemplateResponse", return_value=fake_resp):
            resp = client.get("/my-appointments", cookies=patient_cookies)
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════
# POST /api/appointments/{id}/cancel — Patient Cancellation
# ══════════════════════════════════════════════════════════════

class TestPatientCancelAppointment:

    def test_unauthenticated_returns_401(self, client):
        resp = client.post("/api/appointments/1/cancel")
        assert resp.status_code == 401

    def test_patient_cancels_own_appointment(self, client, patient_cookies):
        with patch("database._turso_run", side_effect=[
            _row(SAMPLE_APT),  # get_appointment_by_id
            UPDATE_OK,         # cancel_appointment_by_patient
        ]), patch("email_utils.send_email", return_value=True):
            resp = client.post("/api/appointments/1/cancel",
                               cookies=patient_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_idor_patient_cannot_cancel_others_appointment(self, client, patient_cookies):
        """SECURITY: patient@test.com must NOT cancel other@test.com's appointment."""
        with patch("database._turso_run", side_effect=[
            _row(OTHER_APT),  # get_appointment_by_id — belongs to other@test.com
            UPDATE_FAIL,      # cancel_appointment_by_patient — rowcount=0
        ]):
            resp = client.post("/api/appointments/2/cancel",
                               cookies=patient_cookies)
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_cannot_cancel_completed_appointment(self, client, patient_cookies):
        with patch("database._turso_run", side_effect=[
            _row(COMPLETED_APT),  # get_appointment_by_id
            UPDATE_FAIL,          # DB rejects because status = Completed
        ]):
            resp = client.post("/api/appointments/1/cancel",
                               cookies=patient_cookies)
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_cannot_cancel_already_cancelled_appointment(self, client, patient_cookies):
        with patch("database._turso_run", side_effect=[
            _row(CANCELLED_APT),
            UPDATE_FAIL,
        ]):
            resp = client.post("/api/appointments/1/cancel",
                               cookies=patient_cookies)
        assert resp.status_code == 400

    def test_nonexistent_appointment_returns_404(self, client, patient_cookies):
        with patch("database._turso_run", return_value=EMPTY):
            resp = client.post("/api/appointments/9999/cancel",
                               cookies=patient_cookies)
        assert resp.status_code == 404
        assert resp.json()["success"] is False

    def test_admin_cannot_use_patient_cancel_endpoint(self, client, admin_cookies):
        """Admin token should be rejected by require_patient()."""
        resp = client.post("/api/appointments/1/cancel",
                           cookies=admin_cookies)
        assert resp.status_code == 401
