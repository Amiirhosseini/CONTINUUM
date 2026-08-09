"""Durable storage engines."""

from pathlib import Path

from continuum.storage.base import (
    CheckpointNotFound,
    ConcurrentWriteError,
    CorruptedRecord,
    RunNotFound,
    SchemaVersionError,
    Storage,
    StorageError,
)
from continuum.storage.sqlite import SQLiteStorage

__all__ = [
    "CheckpointNotFound",
    "ConcurrentWriteError",
    "CorruptedRecord",
    "RunNotFound",
    "SQLiteStorage",
    "SchemaVersionError",
    "Storage",
    "StorageError",
    "open_storage",
]


def open_storage(url: str | Path = ":memory:") -> Storage:
    """Open a storage engine from a URL.

    Supported today: ``sqlite:///path.db``, a bare filesystem path, or
    ``:memory:``. PostgreSQL is a later phase; asking for it fails clearly
    rather than silently falling back to a local file.
    """
    raw = str(url)
    scheme = raw.split("://", 1)[0].lower() if "://" in raw else ""

    if scheme in ("postgres", "postgresql"):
        raise NotImplementedError(
            "PostgreSQL storage is not implemented yet; use sqlite:///path.db"
        )
    if scheme not in ("", "sqlite"):
        raise ValueError(f"unsupported storage URL scheme: {scheme!r}")
    return SQLiteStorage(raw)
