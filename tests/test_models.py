"""
Unit tests for all Pydantic models in models.py.
Tests every validator — valid inputs, edge cases, and error cases.
"""
import pytest
from pydantic import ValidationError
from models import (
    AppointmentForm, ContactForm, LoginForm, RegisterForm,
    ForgotPasswordForm, ResetPasswordForm, ProfileUpdateForm,
    SlotForm, DentalRecordForm, TOTPVerifyForm,
)


# ══════════════════════════════════════════════════════════════
# AppointmentForm
# ══════════════════════════════════════════════════════════════

class TestAppointmentForm:

    def test_valid_appointment(self):
        f = AppointmentForm(
            name="John Doe", phone="9999999999", email="john@example.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM",
            service="Teeth Cleaning", message="Please be gentle"
        )
        assert f.name == "John Doe"
        assert f.email == "john@example.com"

    def test_name_stripped(self):
        f = AppointmentForm(
            name="  Alice  ", phone="9999999999", email="a@b.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
        )
        assert f.name == "Alice"

    def test_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="A", phone="9999999999", email="a@b.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="", phone="9999999999", email="a@b.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_name_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="   ", phone="9999999999", email="a@b.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_phone_with_dashes_valid(self):
        f = AppointmentForm(
            name="John", phone="999-999-9999", email="a@b.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
        )
        assert f.phone == "999-999-9999"

    def test_phone_with_spaces_valid(self):
        f = AppointmentForm(
            name="John", phone="999 999 9999", email="a@b.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
        )
        assert f.phone == "999 999 9999"

    def test_phone_with_parens_valid(self):
        f = AppointmentForm(
            name="John", phone="(999) 999-9999", email="a@b.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
        )
        assert f.phone is not None

    def test_phone_too_short_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="123", email="a@b.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_phone_with_letters_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="ABCDEFGHIJ", email="a@b.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_phone_too_long_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="1234567890123456", email="a@b.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_email_missing_at_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="9999999999", email="johnexample.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_email_missing_domain_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="9999999999", email="john@",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_email_missing_tld_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="9999999999", email="john@example",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_email_with_plus_valid(self):
        f = AppointmentForm(
            name="John", phone="9999999999", email="john+dental@example.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
        )
        assert "john+dental" in f.email

    def test_service_empty_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="9999999999", email="a@b.com",
                preferred_date="2025-12-01", preferred_time="10:00 AM", service=""
            )

    def test_preferred_date_empty_raises(self):
        with pytest.raises(ValidationError):
            AppointmentForm(
                name="John", phone="9999999999", email="a@b.com",
                preferred_date="", preferred_time="10:00 AM", service="Cleaning"
            )

    def test_message_optional(self):
        f = AppointmentForm(
            name="John", phone="9999999999", email="a@b.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
        )
        assert f.message == ""

    def test_unicode_name_valid(self):
        f = AppointmentForm(
            name="Aarav Kumar", phone="9999999999", email="aarav@example.com",
            preferred_date="2025-12-01", preferred_time="10:00 AM", service="Cleaning"
        )
        assert f.name == "Aarav Kumar"


# ══════════════════════════════════════════════════════════════
# ContactForm
# ══════════════════════════════════════════════════════════════

class TestContactForm:

    def test_valid_contact(self):
        f = ContactForm(name="Jane", email="jane@example.com",
                        message="I have a question about pricing.")
        assert f.name == "Jane"

    def test_message_too_short_raises(self):
        with pytest.raises(ValidationError):
            ContactForm(name="Jane", email="jane@example.com", message="Hi")

    def test_message_exactly_10_chars_valid(self):
        f = ContactForm(name="Jane", email="jane@example.com", message="1234567890")
        assert len(f.message) >= 10

    def test_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            ContactForm(name="J", email="jane@example.com", message="Valid message here")

    def test_email_invalid_raises(self):
        with pytest.raises(ValidationError):
            ContactForm(name="Jane", email="not-an-email", message="Valid message here")

    def test_phone_optional(self):
        f = ContactForm(name="Jane", email="jane@example.com",
                        message="Valid message here")
        assert f.phone == ""

    def test_phone_provided(self):
        f = ContactForm(name="Jane", email="jane@example.com",
                        phone="9999999999", message="Valid message here")
        assert f.phone == "9999999999"


# ══════════════════════════════════════════════════════════════
# LoginForm
# ══════════════════════════════════════════════════════════════

class TestLoginForm:

    def test_valid_login(self):
        f = LoginForm(username="admin", password="secret")
        assert f.username == "admin"
        assert f.password == "secret"

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            LoginForm(password="secret")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            LoginForm(username="admin")


# ══════════════════════════════════════════════════════════════
# RegisterForm
# ══════════════════════════════════════════════════════════════

class TestRegisterForm:

    def test_valid_registration(self):
        f = RegisterForm(
            name="New User", email="NEW@EXAMPLE.COM",
            password="password123", confirm_password="password123"
        )
        assert f.email == "new@example.com"  # lowercased

    def test_email_lowercased(self):
        f = RegisterForm(
            name="User", email="USER@EXAMPLE.COM",
            password="pass123", confirm_password="pass123"
        )
        assert f.email == "user@example.com"

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            RegisterForm(
                name="User", email="u@example.com",
                password="abc", confirm_password="abc"
            )

    def test_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            RegisterForm(
                name="U", email="u@example.com",
                password="pass123", confirm_password="pass123"
            )

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            RegisterForm(
                name="User", email="not-valid",
                password="pass123", confirm_password="pass123"
            )

    def test_phone_optional(self):
        f = RegisterForm(
            name="User", email="u@example.com",
            password="pass123", confirm_password="pass123"
        )
        assert f.phone == ""


# ══════════════════════════════════════════════════════════════
# ForgotPasswordForm
# ══════════════════════════════════════════════════════════════

class TestForgotPasswordForm:

    def test_valid_email(self):
        f = ForgotPasswordForm(email="user@example.com")
        assert f.email == "user@example.com"

    def test_email_lowercased(self):
        f = ForgotPasswordForm(email="USER@EXAMPLE.COM")
        assert f.email == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            ForgotPasswordForm(email="not-an-email")


# ══════════════════════════════════════════════════════════════
# ResetPasswordForm
# ══════════════════════════════════════════════════════════════

class TestResetPasswordForm:

    def test_valid_reset(self):
        f = ResetPasswordForm(token="abc123", password="newpass1",
                              confirm_password="newpass1")
        assert f.token == "abc123"

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            ResetPasswordForm(token="abc", password="abc",
                              confirm_password="abc")

    def test_missing_token_raises(self):
        with pytest.raises(ValidationError):
            ResetPasswordForm(password="newpass1", confirm_password="newpass1")


# ══════════════════════════════════════════════════════════════
# ProfileUpdateForm
# ══════════════════════════════════════════════════════════════

class TestProfileUpdateForm:

    def test_valid_profile(self):
        f = ProfileUpdateForm(name="Jane Doe", phone="9999999999")
        assert f.name == "Jane Doe"

    def test_name_stripped(self):
        f = ProfileUpdateForm(name="  Jane  ")
        assert f.name == "Jane"

    def test_name_too_short_raises(self):
        with pytest.raises(ValidationError):
            ProfileUpdateForm(name="J")

    def test_phone_optional(self):
        f = ProfileUpdateForm(name="Jane")
        assert f.phone == ""


# ══════════════════════════════════════════════════════════════
# SlotForm
# ══════════════════════════════════════════════════════════════

class TestSlotForm:

    def test_valid_slot(self):
        f = SlotForm(slot_date="2025-12-01", slot_time="09:00 AM")
        assert f.slot_date == "2025-12-01"

    def test_empty_date_raises(self):
        with pytest.raises(ValidationError):
            SlotForm(slot_date="", slot_time="09:00 AM")

    def test_empty_time_raises(self):
        with pytest.raises(ValidationError):
            SlotForm(slot_date="2025-12-01", slot_time="")

    def test_whitespace_date_raises(self):
        with pytest.raises(ValidationError):
            SlotForm(slot_date="   ", slot_time="09:00 AM")


# ══════════════════════════════════════════════════════════════
# DentalRecordForm
# ══════════════════════════════════════════════════════════════

class TestDentalRecordForm:

    def test_valid_record(self):
        f = DentalRecordForm(file_url="https://example.com/xray.pdf",
                             file_name="xray.pdf", record_type="X-Ray")
        assert f.record_type == "X-Ray"

    def test_record_type_defaults_to_general(self):
        f = DentalRecordForm(file_url="https://example.com/xray.pdf",
                             file_name="xray.pdf")
        assert f.record_type == "General"


# ══════════════════════════════════════════════════════════════
# TOTPVerifyForm
# ══════════════════════════════════════════════════════════════

class TestTOTPVerifyForm:

    def test_valid_totp(self):
        f = TOTPVerifyForm(code="123456")
        assert f.code == "123456"

    def test_missing_code_raises(self):
        with pytest.raises(ValidationError):
            TOTPVerifyForm()
