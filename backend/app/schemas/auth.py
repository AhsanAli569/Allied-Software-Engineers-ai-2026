import re
from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,50}$")
MINIMUM_AGE_YEARS = 18


def calculate_age(born: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    date_of_birth: date

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

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, value: date) -> date:
        today = date.today()
        if value > today:
            raise ValueError("Date of birth cannot be in the future")
        if calculate_age(value, today) < MINIMUM_AGE_YEARS:
            raise ValueError("You must be at least 18 years old to create an ASE AI account")
        return value


class LoginRequest(BaseModel):
    username_or_email: str
    password: str
