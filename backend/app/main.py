from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import chat, export, health

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name)

def get_allowed_origins(origins_str: str) -> list[str]:
    # Remove any accidental quotes and split by comma
    cleaned = origins_str.replace('"', '').replace("'", "")
    origins = [o.strip().rstrip('/') for o in cleaned.split(',') if o.strip()]
    return origins if origins else ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(export.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {"app": settings.app_name, "status": "running"}
