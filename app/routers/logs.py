"""대화 로그 조회 / 추적.

- GET /api/logs         : 내 로그 (JSON, 페이지네이션)
- GET /logs             : 내 로그 화면 (HTML 표)
- GET /api/admin/logs   : 전체 로그 (관리자, 사용자 필터 가능)
- GET /admin/logs       : 전체 로그 화면 (관리자)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatLog, User
from app.schemas import ChatLogItem, ChatLogListResponse
from app.security import require_admin, require_user_api, require_user_page
from app.templates import render

router = APIRouter(tags=["logs"])


@router.get("/api/logs", response_model=ChatLogListResponse)
def my_logs(
    user: User = Depends(require_user_api),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    base = select(ChatLog).where(ChatLog.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(ChatLog.id.desc()).limit(limit).offset(offset)
    ).all()
    return ChatLogListResponse(
        total=total, items=[ChatLogItem.model_validate(r) for r in rows]
    )


@router.get("/logs")
def my_logs_page(
    request: Request,
    user: User = Depends(require_user_page),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(ChatLog)
        .where(ChatLog.user_id == user.id)
        .order_by(ChatLog.id.desc())
        .limit(200)
    ).all()
    return render(request, "logs.html", {"rows": rows, "scope": "내"}, current_user=user)


@router.get("/api/admin/logs", response_model=ChatLogListResponse)
def admin_logs(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    username: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    base = select(ChatLog)
    if username:
        base = base.join(User).where(User.username == username)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(ChatLog.id.desc()).limit(limit).offset(offset)
    ).all()
    return ChatLogListResponse(
        total=total, items=[ChatLogItem.model_validate(r) for r in rows]
    )


@router.get("/admin/logs")
def admin_logs_page(
    request: Request,
    user: User = Depends(require_user_page),
    db: Session = Depends(get_db),
):
    if not user.is_admin:
        return render(
            request,
            "logs.html",
            {"rows": [], "scope": "관리자", "forbidden": True},
            current_user=user,
            status_code=403,
        )
    rows = db.scalars(
        select(ChatLog).order_by(ChatLog.id.desc()).limit(300)
    ).all()
    return render(
        request,
        "logs.html",
        {"rows": rows, "scope": "전체(관리자)", "show_user": True},
        current_user=user,
    )
