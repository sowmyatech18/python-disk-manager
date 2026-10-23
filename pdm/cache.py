"""Caches directory scan results in a SQLite database."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ptdu.models import DirNode

from ptdu.scanner import ScanResult


@dataclass
class CacheEntry:
    """Stores the details saved for one scanned file or directory."""

    path: str
    name: str
    size: int
    is_dir: bool
    mtime: float
    scan_time: float


class ScanCache:
    """Manages cached scan data using SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Set up the cache database and its thread-safety helpers.

        Args:
            db_path: Database location; defaults to ~/.cache/ptdu/cache.db.
        """
        if db_path is None:
            cache_dir = Path.home() / ".cache" / "ptdu"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "cache.db"

        self._db_path: Path = db_path
        self._lock: threading.Lock = threading.Lock()
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Return the database connection assigned to the current thread."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self._db_path))
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self) -> None:
        """Create the cache table and its lookup indexes if needed."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scan_cache (
                        path TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        is_dir INTEGER NOT NULL,
                        mtime REAL NOT NULL,
                        scan_time REAL NOT NULL,
                        parent_path TEXT,
                        FOREIGN KEY (parent_path) REFERENCES scan_cache(path)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_parent_path
                    ON scan_cache(parent_path)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_scan_time
                    ON scan_cache(scan_time)
                    """
                )
                conn.commit()
            finally:
                conn.close()

