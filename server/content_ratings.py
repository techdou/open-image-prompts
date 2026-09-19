#!/usr/bin/env python3
"""Load the offline content-rating sidecar consumed by the gallery API.

The rating pass itself runs on a workstation (scripts/audit_nsfw.py) and
writes data/content-ratings.jsonl, one JSON object per line: a single meta
line followed by one record per image. This module only reads that file - it
never writes, matching the archive's read-only boundary. A missing file or a
missing entry means "unrated"; the gallery gates on explicit nsfw/borderline
values only, so partial rating passes degrade to fewer gated images.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RATINGS_PATH = REPOSITORY_ROOT / "data" / "content-ratings.jsonl"
VALID_RATINGS = ("sfw", "borderline", "nsfw")
# Strictest wins when a prompt spans several images.
_STRICTNESS = {"sfw": 0, "borderline": 1, "nsfw": 2}


class ContentRatings:
    """In-memory index of the JSONL sidecar, reloaded when the file changes."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else Path(
            os.environ.get("OIP_RATINGS_PATH", DEFAULT_RATINGS_PATH)
        )
        self._lock = threading.Lock()
        self._entries: dict[str, str] = {}
        self._meta: dict = {}
        self._mtime: float | None = None
        self._reload()

    def _reload(self) -> None:
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            mtime = None
        entries: dict[str, str] = {}
        meta: dict = {}
        if mtime is not None:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except OSError:
                lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "schema_version" in record:
                    meta = record
                    continue
                key = record.get("k")
                rating = record.get("r")
                if isinstance(key, str) and rating in VALID_RATINGS:
                    entries[key] = rating
        with self._lock:
            self._mtime = mtime
            self._entries = entries
            self._meta = meta

    def _current(self) -> dict[str, str]:
        # The audit pass rewrites the sidecar while this process may be serving;
        # a stat() per lookup is cheap and keeps development restart-free.
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            mtime = None
        if mtime != self._mtime:
            self._reload()
        with self._lock:
            return self._entries

    def image_rating(self, tweet_id: str, image_index: int) -> str | None:
        return self._current().get(f"{tweet_id}/{image_index}")

    def item_rating(self, tweet_id: str, image_indexes: list[int]) -> str | None:
        """Aggregate a prompt-level rating: the strictest image rating wins."""
        best: str | None = None
        entries = self._current()
        for image_index in image_indexes:
            rating = entries.get(f"{tweet_id}/{image_index}")
            if rating is not None and (best is None or _STRICTNESS[rating] > _STRICTNESS[best]):
                best = rating
        return best

    def meta(self) -> dict:
        with self._lock:
            return dict(self._meta)
