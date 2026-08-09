import re

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,50}$")


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.match(value):
            raise ValueError("Username may only contain letters, numbers, dots, dashes and underscores")
        return value

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one letter and one number")
        return value

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info) -> str:
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value


class LoginRequest(BaseModel):
    username_or_email: str
    password: str
