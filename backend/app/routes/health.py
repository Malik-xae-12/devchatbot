from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.db.schema_catalog import catalog, ensure_catalog_loaded, force_refresh
from app.models.chat import HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    schema_loaded = ensure_catalog_loaded() if settings.db_configured else False
    return HealthResponse(
        status="ok",
        db_configured=settings.db_configured,
        schema_loaded=schema_loaded or catalog.is_loaded,
    )


@router.get("/catalog")
async def catalog_debug() -> dict:
    """Debug view of exactly what the SQL agents currently see — use this to
    confirm a virtual view (or any table) is actually loaded, instead of
    guessing from chat behavior."""
    ensure_catalog_loaded()
    return {
        "table_count": len(catalog.all_tables()),
        "tables": [
            {
                "name": t.full_name,
                "is_virtual": t.is_virtual,
                "column_count": len(t.columns),
                "description": t.description,
            }
            for t in catalog.all_tables()
        ],
    }


@router.post("/refresh-catalog")
async def refresh_catalog() -> dict:
    """Force-reload the schema catalog from the DB right now. Call this after
    any change to app/db/virtual_views.py or KNOWN_DESCRIPTIONS instead of
    restarting the whole backend."""
    ok = force_refresh()
    return {"refreshed": ok, "table_count": len(catalog.all_tables())}
