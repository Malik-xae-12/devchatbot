from __future__ import annotations

from fastapi import APIRouter

from app.agents.orchestrator import handle_message
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await handle_message(request.message)
