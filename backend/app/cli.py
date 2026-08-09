"""Usage:
  python -m app.cli create-admin
  python -m app.cli ingest-knowledge <file-or-directory>
"""

import asyncio
import getpass
import sys
from pathlib import Path

from sqlalchemy import or_, select

from app.auth.security import hash_password
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.providers.factory import close_all_providers, get_provider
from app.schemas.auth import RegisterRequest
from app.services.document_service import extract_text
from app.services.knowledge_service import ingest_document


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


_EXTENSION_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/plain",
}


def _read_text(path: Path) -> str:
    mime_type = _EXTENSION_MIME_TYPES.get(path.suffix.lower())
    if mime_type is None:
        raise ValueError(f"Unsupported file type: {path.suffix} (supported: {', '.join(_EXTENSION_MIME_TYPES)})")
    return extract_text(mime_type, path.read_bytes())


async def ingest_knowledge(target: str) -> None:
    path = Path(target)
    if not path.exists():
        print(f"\nNo such file or directory: {target}")
        sys.exit(1)

    files = [path] if path.is_file() else sorted(p for p in path.iterdir() if p.suffix.lower() in _EXTENSION_MIME_TYPES)
    if not files:
        print(f"\nNo supported files found (looked for {', '.join(_EXTENSION_MIME_TYPES)}) in {target}")
        sys.exit(1)

    provider = get_provider("gemini")
    try:
        async with AsyncSessionLocal() as db:
            for file_path in files:
                text = _read_text(file_path)
                if not text.strip():
                    print(f"  skipped {file_path.name} (no extractable text)")
                    continue
                count = await ingest_document(db, provider, file_path.name, text)
                print(f"  ingested {file_path.name}: {count} chunks")
    finally:
        await close_all_providers()

    print("\nDone. Re-run this command any time to update the knowledge base — re-ingesting")
    print("a file with the same name replaces its previous chunks.")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "create-admin":
        asyncio.run(create_admin())
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "ingest-knowledge":
        asyncio.run(ingest_knowledge(sys.argv[2]))
        return
    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    main()
