"""챗봇 질문/응답 API + 채팅 페이지.

파이프라인: 질문 수신 → 컨텍스트 구성 → AI 호출 → 응답 반환 → 대화 로그 저장
모든 단계는 서버 로그에 이벤트로 남는다.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_client import AIServiceError, generate_reply
from app.config import get_settings
from app.database import get_db
from app.models import ChatLog, User
from app.schemas import ChatRequest, ChatResponse
from app.security import get_current_user, require_user_api, require_user_page
from app.templates import render

logger = logging.getLogger("chatbot.chat")
router = APIRouter(tags=["chat"])
settings = get_settings()

USER_FACING_ERROR = "AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."


def _recent_history(db: Session, user_id: int) -> list[tuple[str, str]]:
    """같은 사용자의 최근 성공 Q/A 를 오래된 순으로 반환 (문맥 유지용)."""
    n = settings.ai_max_context_messages
    rows = db.scalars(
        select(ChatLog)
        .where(ChatLog.user_id == user_id, ChatLog.status == "success")
        .order_by(ChatLog.id.desc())
        .limit(n)
    ).all()
    return [(r.question, r.answer) for r in reversed(rows)]


@router.get("/chat")
def chat_page(
    request: Request,
    user: User = Depends(require_user_page),
    db: Session = Depends(get_db),
):
    history = db.scalars(
        select(ChatLog)
        .where(ChatLog.user_id == user.id)
        .order_by(ChatLog.id.desc())
        .limit(30)
    ).all()
    return render(
        request,
        "chat.html",
        {"history": list(reversed(history))},
        current_user=user,
    )


@router.post("/api/chat", response_model=ChatResponse)
def api_chat(
    payload: ChatRequest,
    request: Request,
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
):
    question = payload.message
    logger.info("request received: user=%s question_len=%d", user.username, len(question))

    history = _recent_history(db, user.id)

    # ---- AI 호출 ----
    logger.info(
        "AI call: user=%s model=%s context_pairs=%d",
        user.username,
        settings.anthropic_model if settings.ai_enabled else "mock",
        len(history),
    )
    try:
        result = generate_reply(question, history)
        logger.info(
            "AI response received: user=%s latency_ms=%d mocked=%s",
            user.username,
            result.latency_ms,
            result.mocked,
        )
    except AIServiceError as exc:
        logger.error("AI call failed: user=%s error=%s", user.username, exc)
        _save_log(
            db, user.id, question, answer="", status="error",
            error_detail=str(exc), latency_ms=None,
        )
        return JSONResponse(status_code=503, content={"detail": USER_FACING_ERROR})

    # ---- 대화 로그 저장 ----
    log = _save_log(
        db, user.id, question, answer=result.answer, status="success",
        error_detail=None, latency_ms=result.latency_ms,
    )
    if log is None:
        # 저장 실패해도 사용자에게는 답변을 돌려준다.
        return JSONResponse(
            status_code=200,
            content={
                "answer": result.answer,
                "log_id": -1,
                "created_at": None,
                "mocked": result.mocked,
            },
        )

    return ChatResponse(
        answer=result.answer,
        log_id=log.id,
        created_at=log.created_at,
        mocked=result.mocked,
    )


def _save_log(
    db: Session,
    user_id: int,
    question: str,
    *,
    answer: str,
    status: str,
    error_detail: str | None,
    latency_ms: int | None,
) -> ChatLog | None:
    log = ChatLog(
        user_id=user_id,
        question=question,
        answer=answer,
        status=status,
        error_detail=error_detail,
        latency_ms=latency_ms,
    )
    try:
        db.add(log)
        db.commit()
        db.refresh(log)
        logger.info("DB save success: chat_log_id=%s status=%s", log.id, status)
        return log
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("DB save failed: user_id=%s error=%s", user_id, exc)
        return None
