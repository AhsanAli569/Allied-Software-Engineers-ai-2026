import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def _storage_root() -> Path:
    root = Path(settings.storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_file(user_id: uuid.UUID, extension: str, content: bytes) -> str:
    """Writes `content` under a UUID filename (never the user-supplied name — that's kept
    only as display metadata in the DB) and returns the storage_key to persist.
    """
    user_dir = _storage_root() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    key_name = f"{uuid.uuid4().hex}{extension}"
    (user_dir / key_name).write_bytes(content)
    return f"{user_id}/{key_name}"


def _resolve(storage_key: str) -> Path:
    root = _storage_root()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise ValueError("storage_key resolves outside the storage root")
    return path


def read_file(storage_key: str) -> bytes:
    return _resolve(storage_key).read_bytes()


def delete_file(storage_key: str) -> None:
    _resolve(storage_key).unlink(missing_ok=True)
