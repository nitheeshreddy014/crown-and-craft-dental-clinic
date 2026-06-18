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
