"""요청/응답 Pydantic 스키마."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.config import get_settings

settings = get_settings()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=settings.max_question_length)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("빈 질문은 보낼 수 없습니다.")
        return v


class ChatResponse(BaseModel):
    answer: str
    log_id: int
    created_at: datetime
    mocked: bool


class ChatLogItem(BaseModel):
    id: int
    question: str
    answer: str
    status: str
    error_detail: str | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatLogListResponse(BaseModel):
    total: int
    items: list[ChatLogItem]
