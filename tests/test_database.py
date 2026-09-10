"""
Unit tests for database.py helper functions.
All Turso HTTP calls are mocked — no real network calls made.
"""
import pytest
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════════════
# _turso_arg — type conversion
# ══════════════════════════════════════════════════════════════

class TestTursoArg:

    def setup_method(self):
        from database import _turso_arg
        self.fn = _turso_arg

    def test_none_becomes_null(self):
        assert self.fn(None) == {"type": "null", "value": None}

    def test_int_becomes_integer(self):
        assert self.fn(42) == {"type": "integer", "value": "42"}

    def test_bool_true_becomes_integer_1(self):
        assert self.fn(True) == {"type": "integer", "value": "1"}

    def test_bool_false_becomes_integer_0(self):
        assert self.fn(False) == {"type": "integer", "value": "0"}

    def test_float_becomes_float(self):
        assert self.fn(3.14) == {"type": "float", "value": "3.14"}

    def test_string_becomes_text(self):
        assert self.fn("hello") == {"type": "text", "value": "hello"}

    def test_empty_string_becomes_text(self):
        assert self.fn("") == {"type": "text", "value": ""}


# ══════════════════════════════════════════════════════════════
# _turso_cast — type conversion from response
# ══════════════════════════════════════════════════════════════

class TestTursoCast:

    def setup_method(self):
        from database import _turso_cast
        self.fn = _turso_cast

    def test_null_cell_returns_none(self):
        assert self.fn({"type": "null"}) is None

    def test_null_cell_with_no_value_key(self):
        # Turso omits 'value' for NULL — must not raise KeyError
        assert self.fn({"type": "null"}) is None

    def test_integer_cell(self):
        assert self.fn({"type": "integer", "value": "5"}) == 5

    def test_float_cell(self):
        assert self.fn({"type": "float", "value": "3.14"}) == 3.14

    def test_text_cell(self):
        assert self.fn({"type": "text", "value": "hello"}) == "hello"


# ══════════════════════════════════════════════════════════════
# _turso_run — HTTP executor
# ══════════════════════════════════════════════════════════════

class TestTursoRun:

    def _mock_response(self, body: dict, status: int = 200):
        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps(body).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_raises_on_turso_error_result(self):
        from database import _turso_run
        body = {"results": [{"type": "error", "error": {"message": "table not found"}}]}
        with patch("urllib.request.urlopen", return_value=self._mock_response(body)):
            with pytest.raises(RuntimeError, match="Turso error"):
                _turso_run("SELECT 1")

    def test_raises_on_http_error(self):
        import urllib.error
        from database import _turso_run
        err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=None)
        err.read = lambda: b"Unauthorized"
        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(RuntimeError, match="Turso HTTP 401"):
                _turso_run("SELECT 1")

    def test_raises_on_url_error(self):
        import urllib.error
        from database import _turso_run
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("Connection refused")):
            with pytest.raises(RuntimeError, match="connection error"):
                _turso_run("SELECT 1")

    def test_returns_rows_on_success(self):
        from database import _turso_run
        body = {"results": [{"type": "ok", "response": {"type": "ok", "result": {
            "cols": [{"name": "id"}],
            "rows": [[{"type": "integer", "value": "1"}]],
            "last_insert_rowid": "1",
            "affected_row_count": 0,
        }}}]}
        with patch("urllib.request.urlopen", return_value=self._mock_response(body)):
            result = _turso_run("SELECT 1")
        assert result["rows"] == [{"id": 1}]
        assert result["lastrowid"] == 1


# ══════════════════════════════════════════════════════════════
# CRUD function tests (all _turso_run mocked)
# ══════════════════════════════════════════════════════════════

EMPTY = {"rows": [], "lastrowid": None, "rowcount": 0}
INSERT_OK = {"rows": [], "lastrowid": 99, "rowcount": 1}
UPDATE_OK = {"rows": [], "lastrowid": None, "rowcount": 1}
UPDATE_FAIL = {"rows": [], "lastrowid": None, "rowcount": 0}


class TestAddAppointment:

    def test_returns_lastrowid(self):
        with patch("database._turso_run", return_value=INSERT_OK):
            from database import add_appointment
            aid = add_appointment("John", "9999999999", "j@test.com",
                                  "2025-12-01", "10:00 AM", "Cleaning", "")
        assert aid == 99


class TestGetAppointments:

    def test_returns_empty_list_when_no_results(self):
        with patch("database._turso_run", return_value=EMPTY):
            from database import get_appointments
            result = get_appointments()
        assert result == []

    def test_search_filter_applied(self):
        with patch("database._turso_run", return_value=EMPTY) as mock_run:
            from database import get_appointments
            get_appointments(search="john")
            sql = mock_run.call_args[0][0]
            assert "LIKE" in sql

    def test_status_filter_applied(self):
        with patch("database._turso_run", return_value=EMPTY) as mock_run:
            from database import get_appointments
            get_appointments(status_filter="Confirmed")
            sql = mock_run.call_args[0][0]
            assert "appointment_status" in sql

    def test_all_status_filter_ignored(self):
        with patch("database._turso_run", return_value=EMPTY) as mock_run:
            from database import get_appointments
            get_appointments(status_filter="All")
            sql = mock_run.call_args[0][0]
            assert "appointment_status" not in sql


class TestGetAppointmentById:

    def test_returns_none_when_not_found(self):
        with patch("database._turso_run", return_value=EMPTY):
            from database import get_appointment_by_id
            assert get_appointment_by_id(999) is None

    def test_returns_first_row_when_found(self):
        row = {"id": 1, "name": "John"}
        with patch("database._turso_run", return_value={"rows": [row], "lastrowid": None, "rowcount": 0}):
            from database import get_appointment_by_id
            assert get_appointment_by_id(1) == row


class TestUpdateAppointmentStatus:

    def test_returns_true_when_updated(self):
        with patch("database._turso_run", return_value=UPDATE_OK):
            from database import update_appointment_status
            assert update_appointment_status(1, "Confirmed") is True

    def test_returns_false_when_not_found(self):
        with patch("database._turso_run", return_value=UPDATE_FAIL):
            from database import update_appointment_status
            assert update_appointment_status(999, "Confirmed") is False


class TestCancelAppointmentByPatient:

    def test_returns_true_on_success(self):
        with patch("database._turso_run", return_value=UPDATE_OK):
            from database import cancel_appointment_by_patient
            assert cancel_appointment_by_patient(1, "patient@test.com") is True

    def test_returns_false_when_not_owner_or_already_cancelled(self):
        with patch("database._turso_run", return_value=UPDATE_FAIL):
            from database import cancel_appointment_by_patient
            assert cancel_appointment_by_patient(1, "other@test.com") is False


class TestUserFunctions:

    def test_check_email_exists_true(self):
        with patch("database._turso_run", return_value={"rows": [{"1": 1}], "lastrowid": None, "rowcount": 0}):
            from database import check_email_exists
            assert check_email_exists("user@test.com") is True

    def test_check_email_exists_false(self):
        with patch("database._turso_run", return_value=EMPTY):
            from database import check_email_exists
            assert check_email_exists("unknown@test.com") is False

    def test_get_user_by_email_returns_none_when_not_found(self):
        with patch("database._turso_run", return_value=EMPTY):
            from database import get_user_by_email
            assert get_user_by_email("ghost@test.com") is None

    def test_get_user_by_email_returns_user(self):
        user = {"id": 1, "email": "user@test.com", "name": "User"}
        with patch("database._turso_run", return_value={"rows": [user], "lastrowid": None, "rowcount": 0}):
            from database import get_user_by_email
            assert get_user_by_email("user@test.com") == user

    def test_get_user_by_reset_token_returns_none(self):
        with patch("database._turso_run", return_value=EMPTY):
            from database import get_user_by_reset_token
            assert get_user_by_reset_token("bad-token") is None


class TestSlotFunctions:

    def test_add_slot_returns_true_on_success(self):
        with patch("database._turso_run", return_value=INSERT_OK):
            from database import add_slot
            assert add_slot("2025-12-01", "10:00 AM") is True

    def test_add_slot_returns_false_on_exception(self):
        with patch("database._turso_run", side_effect=Exception("UNIQUE constraint")):
            from database import add_slot
            assert add_slot("2025-12-01", "10:00 AM") is False

    def test_delete_slot_returns_true(self):
        with patch("database._turso_run", return_value=UPDATE_OK):
            from database import delete_slot
            assert delete_slot(1) is True

    def test_delete_slot_returns_false_when_not_found(self):
        with patch("database._turso_run", return_value=UPDATE_FAIL):
            from database import delete_slot
            assert delete_slot(999) is False


class TestDentalRecords:

    def test_delete_dental_record_own_record(self):
        with patch("database._turso_run", return_value=UPDATE_OK):
            from database import delete_dental_record
            assert delete_dental_record(1, "patient@test.com") is True

    def test_delete_dental_record_wrong_user(self):
        with patch("database._turso_run", return_value=UPDATE_FAIL):
            from database import delete_dental_record
            assert delete_dental_record(1, "other@test.com") is False
