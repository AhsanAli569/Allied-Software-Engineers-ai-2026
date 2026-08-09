"""Usage: python -m app.cli create-admin"""

import asyncio
import getpass
import sys

from sqlalchemy import or_, select

from app.auth.security import hash_password
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest


async def create_admin() -> None:
    print("Create the first ASE AI administrator account.\n")
    full_name = input("Full name: ").strip()
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    try:
        RegisterRequest(full_name=full_name, username=username, email=email, password=password, confirm_password=confirm)
    except Exception as exc:
        print(f"\nInvalid input: {exc}")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(or_(User.username == username, User.email == email)))
        if existing.scalar_one_or_none():
            print("\nA user with that username or email already exists.")
            sys.exit(1)

        admin = User(
            full_name=full_name,
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.super_admin,
        )
        db.add(admin)
        await db.commit()

    print(f"\nAdministrator '{username}' created successfully.")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "create-admin":
        print("Usage: python -m app.cli create-admin")
        sys.exit(1)
    asyncio.run(create_admin())


if __name__ == "__main__":
    main()
