from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: str
    sql: str | None = None
    row_count: int | None = None
    # Set when row_count exceeds the excel-export threshold: the full result
    # set is cached server-side and downloadable via /api/export/{export_id}.
    export_id: str | None = None
    export_row_count: int | None = None


class HealthResponse(BaseModel):
    status: str
    db_configured: bool
    schema_loaded: bool
