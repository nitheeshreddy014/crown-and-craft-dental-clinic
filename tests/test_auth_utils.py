"""
Unit tests for JWT token creation/verification and password hashing utilities.
No DB or SMTP calls needed — pure function tests.
"""
import os, time, hashlib, pytest

os.environ.setdefault("ADMIN_PASSWORD", "TestAdmin123")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("TURSO_DATABASE_URL", "libsql://fake.turso.io")
os.environ.setdefault("TURSO_AUTH_TOKEN", "fake-token")

from unittest.mock import patch
EMPTY = {"rows": [], "lastrowid": None, "rowcount": 0}


# ══════════════════════════════════════════════════════════════
# JWT — create_token / verify_token
# ══════════════════════════════════════════════════════════════

class TestCreateToken:

    def test_creates_decodable_token(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import create_token, verify_token
            token = create_token("user@test.com", "patient", "Test User")
            payload = verify_token(token)
            assert payload is not None

    def test_token_contains_correct_sub(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import create_token, verify_token
            token = create_token("user@test.com", "patient", "Test User")
            payload = verify_token(token)
            assert payload["sub"] == "user@test.com"

    def test_token_contains_correct_role(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import create_token, verify_token
            token = create_token("admin", "admin", "Admin")
            payload = verify_token(token)
            assert payload["role"] == "admin"

    def test_token_contains_correct_name(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import create_token, verify_token
            token = create_token("user@test.com", "patient", "Jane Doe")
            payload = verify_token(token)
            assert payload["name"] == "Jane Doe"

    def test_patient_token_role(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import create_token, verify_token
            token = create_token("p@test.com", "patient", "Patient")
            payload = verify_token(token)
            assert payload["role"] == "patient"


class TestVerifyToken:

    def test_valid_token_returns_payload(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import create_token, verify_token
            token = create_token("u@test.com", "patient", "U")
            assert verify_token(token) is not None

    def test_tampered_token_returns_none(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import create_token, verify_token
            token = create_token("u@test.com", "patient", "U")
            tampered = token[:-5] + "XXXXX"
            assert verify_token(tampered) is None

    def test_garbage_string_returns_none(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import verify_token
            assert verify_token("not.a.token") is None

    def test_empty_string_returns_none(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import verify_token
            assert verify_token("") is None

    def test_expired_token_returns_none(self):
        """Create a token with a past expiry using jose directly."""
        with patch("database._turso_run", return_value=EMPTY):
            from jose import jwt
            from main import SECRET_KEY, ALGORITHM
            payload = {"sub": "u@test.com", "role": "patient",
                       "name": "U", "exp": int(time.time()) - 3600}
            expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
            from main import verify_token
            assert verify_token(expired_token) is None


# ══════════════════════════════════════════════════════════════
# Password hashing — _hash_pw / _verify_pw
# ══════════════════════════════════════════════════════════════

class TestPasswordHashing:

    def test_hash_is_consistent(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import _hash_pw
            assert _hash_pw("password123") == _hash_pw("password123")

    def test_hash_is_sha256(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import _hash_pw
            expected = hashlib.sha256("password123".encode()).hexdigest()
            assert _hash_pw("password123") == expected

    def test_different_passwords_produce_different_hashes(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import _hash_pw
            assert _hash_pw("password1") != _hash_pw("password2")

    def test_verify_correct_password_returns_true(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import _hash_pw, _verify_pw
            hashed = _hash_pw("mypassword")
            assert _verify_pw("mypassword", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import _hash_pw, _verify_pw
            hashed = _hash_pw("mypassword")
            assert _verify_pw("wrongpassword", hashed) is False

    def test_verify_empty_password_returns_false(self):
        with patch("database._turso_run", return_value=EMPTY):
            from main import _hash_pw, _verify_pw
            hashed = _hash_pw("mypassword")
            assert _verify_pw("", hashed) is False
