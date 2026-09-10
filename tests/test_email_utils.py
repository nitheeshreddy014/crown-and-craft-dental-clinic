"""
Unit tests for email_utils.py.
All SMTP calls are mocked — no real emails are sent.
"""
import os, pytest
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════════════
# send_email — core sender
# ══════════════════════════════════════════════════════════════

class TestSendEmail:

    def test_returns_false_when_no_credentials(self):
        with patch.dict(os.environ, {"GMAIL_USER": "", "GMAIL_APP_PASSWORD": ""}):
            import importlib, email_utils
            importlib.reload(email_utils)
            result = email_utils.send_email("to@test.com", "Subject", "<p>body</p>")
            assert result is False

    def test_returns_true_on_successful_smtp(self):
        with patch("email_utils.GMAIL_USER", "clinic@gmail.com"), \
             patch("email_utils.GMAIL_APP_PASSWORD", "apppass"), \
             patch("smtplib.SMTP_SSL") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = lambda s: mock_server
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            import email_utils
            result = email_utils.send_email("to@test.com", "Hello", "<p>Hi</p>")
            assert result is True

    def test_returns_false_on_smtp_exception(self):
        with patch("email_utils.GMAIL_USER", "clinic@gmail.com"), \
             patch("email_utils.GMAIL_APP_PASSWORD", "apppass"), \
             patch("smtplib.SMTP_SSL", side_effect=Exception("SMTP error")):
            import email_utils
            result = email_utils.send_email("to@test.com", "Hello", "<p>Hi</p>")
            assert result is False


# ══════════════════════════════════════════════════════════════
# _wrap — HTML wrapper
# ══════════════════════════════════════════════════════════════

class TestWrap:

    def test_wrap_contains_clinic_name(self):
        import email_utils
        html = email_utils._wrap("<p>test</p>")
        assert "Crown &amp; Craft Dental Clinic" in html or "Crown" in html

    def test_wrap_contains_body_html(self):
        import email_utils
        html = email_utils._wrap("<p>Hello World</p>")
        assert "<p>Hello World</p>" in html

    def test_wrap_contains_doctype(self):
        import email_utils
        html = email_utils._wrap("<p>x</p>")
        assert "<!DOCTYPE html>" in html


# ══════════════════════════════════════════════════════════════
# send_booking_confirmation
# ══════════════════════════════════════════════════════════════

class TestSendBookingConfirmation:

    def test_calls_send_email_with_correct_subject(self):
        import email_utils
        with patch.object(email_utils, "send_email", return_value=True) as mock_send:
            email_utils.send_booking_confirmation(
                "patient@test.com", "John", "2025-12-01", "10:00 AM", "Teeth Cleaning", 42
            )
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "Teeth Cleaning" in args[1]
            assert "2025-12-01" in args[1]

    def test_body_contains_appointment_id(self):
        import email_utils
        captured = {}
        def capture(to, subject, body):
            captured["body"] = body
            return True
        with patch.object(email_utils, "send_email", side_effect=capture):
            email_utils.send_booking_confirmation(
                "p@test.com", "Jane", "2025-12-01", "10:00 AM", "Cleaning", 99
            )
        assert "#99" in captured["body"]


# ══════════════════════════════════════════════════════════════
# send_status_update
# ══════════════════════════════════════════════════════════════

class TestSendStatusUpdate:

    @pytest.mark.parametrize("status,icon", [
        ("Confirmed", "✅"),
        ("Cancelled", "❌"),
        ("Completed", "🏆"),
        ("Pending",   "⏳"),
    ])
    def test_subject_contains_status_and_icon(self, status, icon):
        import email_utils
        with patch.object(email_utils, "send_email", return_value=True) as mock_send:
            email_utils.send_status_update(
                "p@test.com", "John", "2025-12-01", "10:00 AM", "Cleaning", status
            )
            subject = mock_send.call_args[0][1]
            assert status in subject
            assert icon in subject


# ══════════════════════════════════════════════════════════════
# send_reminder
# ══════════════════════════════════════════════════════════════

class TestSendReminder:

    def test_subject_contains_time(self):
        import email_utils
        with patch.object(email_utils, "send_email", return_value=True) as mock_send:
            email_utils.send_reminder("p@test.com", "John", "2025-12-01", "09:30 AM", "Cleaning")
            subject = mock_send.call_args[0][1]
            assert "09:30 AM" in subject

    def test_body_contains_tomorrow_reference(self):
        import email_utils
        captured = {}
        def capture(to, subject, body):
            captured["body"] = body
            return True
        with patch.object(email_utils, "send_email", side_effect=capture):
            email_utils.send_reminder("p@test.com", "Jane", "2025-12-01", "10:00 AM", "Cleaning")
        assert "tomorrow" in captured["body"].lower()


# ══════════════════════════════════════════════════════════════
# send_password_reset
# ══════════════════════════════════════════════════════════════

class TestSendPasswordReset:

    def test_body_contains_reset_token_url(self):
        import email_utils
        captured = {}
        def capture(to, subject, body):
            captured["body"] = body
            return True
        with patch.object(email_utils, "send_email", side_effect=capture):
            email_utils.send_password_reset("u@test.com", "Jane", "abc123token")
        assert "abc123token" in captured["body"]
        assert "reset-password" in captured["body"]

    def test_subject_contains_reset_keyword(self):
        import email_utils
        with patch.object(email_utils, "send_email", return_value=True) as mock_send:
            email_utils.send_password_reset("u@test.com", "Jane", "token123")
            subject = mock_send.call_args[0][1]
            assert "Reset" in subject or "Password" in subject


# ══════════════════════════════════════════════════════════════
# send_cancellation_confirmation
# ══════════════════════════════════════════════════════════════

class TestSendCancellationConfirmation:

    def test_subject_contains_cancelled(self):
        import email_utils
        with patch.object(email_utils, "send_email", return_value=True) as mock_send:
            email_utils.send_cancellation_confirmation(
                "p@test.com", "John", "2025-12-01", "10:00 AM", "Cleaning"
            )
            subject = mock_send.call_args[0][1]
            assert "Cancelled" in subject or "Cancel" in subject
