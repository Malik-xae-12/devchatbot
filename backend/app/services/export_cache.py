from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings


@dataclass
class ExportEntry:
    rows: list[dict[str, Any]]
    question: str
    created_at: float = field(default_factory=time.time)


class ExportCache:
    """Tiny in-memory store so a chat reply can hand back a short-lived
    download link instead of dumping hundreds of rows into the conversation.

    Not meant to survive a process restart or scale across workers — if this
    app grows beyond a single dev/demo instance, swap this for Redis or a
    Fabric-backed staging table.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ExportEntry] = {}

    def _evict_expired(self) -> None:
        cutoff = time.time() - settings.export_cache_ttl_seconds
        expired = [key for key, entry in self._entries.items() if entry.created_at < cutoff]
        for key in expired:
            self._entries.pop(key, None)

    def store(self, rows: list[dict[str, Any]], question: str) -> str:
        self._evict_expired()
        export_id = uuid.uuid4().hex
        self._entries[export_id] = ExportEntry(rows=rows, question=question)
        return export_id

    def get(self, export_id: str) -> ExportEntry | None:
        self._evict_expired()
        return self._entries.get(export_id)


export_cache = ExportCache()
