"""Local filesystem storage standing in for AWS S3 — same interface
(`save`/`read`/`delete` by key) so swapping to a real S3 client later is a
drop-in change, not a rewrite.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from .config import UPLOAD_DIR


def save(filename: str, content: bytes) -> str:
    key = f"{uuid.uuid4().hex}_{filename}"
    path = UPLOAD_DIR / key
    path.write_bytes(content)
    return str(path)


def read(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()


def delete(storage_path: str) -> None:
    Path(storage_path).unlink(missing_ok=True)
