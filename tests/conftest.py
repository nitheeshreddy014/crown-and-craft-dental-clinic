"""
Shared fixtures for all test files.
- Patches _turso_run so no real DB calls are made.
- Patches send_email so no real SMTP calls are made.
- Provides pre-baked JWT cookies for patient and admin.
"""
import os, hashlib, pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ── Env vars must be set BEFORE importing main ────────────────────────────────
os.environ.setdefault("ADMIN_PASSWORD", "TestAdmin123")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("TURSO_DATABASE_URL", "libsql://fake.turso.io")
os.environ.setdefault("TURSO_AUTH_TOKEN", "fake-token")
os.environ.setdefault("GMAIL_USER", "")
os.environ.setdefault("GMAIL_APP_PASSWORD", "")
os.environ.setdefault("CRON_SECRET", "test-cron-secret")

# ── Default mock DB result ────────────────────────────────────────────────────
EMPTY_RESULT = {"rows": [], "lastrowid": None, "rowcount": 0}


def _make_result(rows=None, lastrowid=None, rowcount=0):
    return {"rows": rows or [], "lastrowid": lastrowid, "rowcount": rowcount}


# ── App client (DB + email mocked) ────────────────────────────────────────────
@pytest.fixture(scope="session")
def mock_db():
    """Session-scoped patch of _turso_run — returns empty by default."""
    with patch("database._turso_run", return_value=EMPTY_RESULT) as m:
        yield m


@pytest.fixture(scope="session")
def mock_batch():
    with patch("database._turso_batch", return_value=[EMPTY_RESULT] * 4) as m:
        yield m


@pytest.fixture(scope="session")
def mock_email():
    with patch("email_utils.send_email", return_value=True) as m:
        yield m


@pytest.fixture(scope="session")
def client(mock_db, mock_batch, mock_email):
    from main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Token helpers ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def patient_token():
    from main import create_token
    return create_token("patient@test.com", "patient", "Test Patient")


@pytest.fixture(scope="session")
def admin_token():
    from main import create_token
    return create_token("nitheesh", "admin", "Nitheesh")


@pytest.fixture(scope="session")
def patient_cookies(patient_token):
    return {"admin_token": patient_token}


@pytest.fixture(scope="session")
def admin_cookies(admin_token):
    return {"admin_token": admin_token}


# ── Sample data ───────────────────────────────────────────────────────────────
SAMPLE_USER = {
    "id": 1,
    "name": "Test Patient",
    "email": "patient@test.com",
    "phone": "9999999999",
    "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
    "role": "patient",
    "auth_provider": "email",
    "reset_token": None,
    "reset_token_expiry": None,
    "totp_secret": None,
}

SAMPLE_APPOINTMENT = {
    "id": 1,
    "name": "Test Patient",
    "phone": "9999999999",
    "email": "patient@test.com",
    "preferred_date": "2025-12-01",
    "preferred_time": "10:00 AM",
    "service": "Teeth Cleaning",
    "message": "",
    "appointment_status": "Pending",
    "created_at": "2025-01-01 10:00:00",
}

SAMPLE_SLOT = {
    "id": 1,
    "slot_date": "2025-12-01",
    "slot_time": "10:00 AM",
    "is_available": 1,
    "created_at": "2025-01-01 10:00:00",
}

SAMPLE_RECORD = {
    "id": 1,
    "user_email": "patient@test.com",
    "file_url": "https://example.com/file.pdf",
    "file_name": "xray.pdf",
    "record_type": "X-Ray",
    "uploaded_at": "2025-01-01 10:00:00",
}
