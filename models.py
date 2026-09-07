from pydantic import BaseModel, field_validator
from typing import Optional
import re

class AppointmentForm(BaseModel):
    name: str
    phone: str
    email: str
    preferred_date: str
    preferred_time: str
    service: str
    message: Optional[str] = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        cleaned = re.sub(r"[\s\-\(\)\+]", "", v)
        if not cleaned.isdigit() or len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError("Invalid phone number")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email address")
        return v.strip()

    @field_validator("preferred_date", "preferred_time", "service")
    @classmethod
    def validate_required(cls, v):
        if not v or not v.strip():
            raise ValueError("This field is required")
        return v.strip()


class ContactForm(BaseModel):
    name: str
    email: str
    phone: Optional[str] = ""
    message: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email address")
        return v.strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Message must be at least 10 characters")
        return v.strip()


class LoginForm(BaseModel):
    username: str
    password: str


class RegisterForm(BaseModel):
    name: str
    email: str
    phone: Optional[str] = ""
    password: str
    confirm_password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email address")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class ForgotPasswordForm(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email")
        return v.strip().lower()


class ResetPasswordForm(BaseModel):
    token: str
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class ProfileUpdateForm(BaseModel):
    name: str
    phone: Optional[str] = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()


class SlotForm(BaseModel):
    slot_date: str
    slot_time: str

    @field_validator("slot_date", "slot_time")
    @classmethod
    def validate_required(cls, v):
        if not v or not v.strip():
            raise ValueError("This field is required")
        return v.strip()


class DentalRecordForm(BaseModel):
    file_url: str
    file_name: str
    record_type: Optional[str] = "General"


class TOTPVerifyForm(BaseModel):
    code: str
