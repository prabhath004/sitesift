"""Local PDF storage helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_pdf(content: bytes, *, document_id: str, storage_dir: str) -> Path:
    """Store an uploaded PDF under a deterministic local development path."""
    directory = Path(storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{document_id}.pdf"
    path.write_bytes(content)
    return path


def read_pdf(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
