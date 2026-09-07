"""FastAPI 애플리케이션 진입점.

라우팅
------
GET  /            홈
GET/POST /register, /login   인증
POST /logout
GET  /chat                   채팅 화면 (로그인 필요)
POST /api/chat               질문/응답 API (로그인 필요)
GET  /logs, /api/logs        내 대화 로그
GET  /admin/logs, /api/admin/logs   관리자 로그
GET  /healthz                헬스체크
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, init_db
from app.logging_config import setup_logging
from app.models import User
from app.routers import auth, chat, logs
from app.security import _RedirectException, redirect_exception_handler
from app.templates import render

setup_logging()
logger = logging.getLogger("chatbot")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info(
        "app start | model=%s | ai_enabled=%s | db=%s",
        settings.anthropic_model,
        settings.ai_enabled,
        settings.database_url,
    )
    if not settings.ai_enabled:
        logger.warning("ANTHROPIC_API_KEY 미설정 → mock 응답 모드로 동작합니다.")
    if settings.session_secret == "change-me-to-a-long-random-string":
        logger.warning("SESSION_SECRET 이 기본값입니다. 배포 전 반드시 교체하세요.")
    yield


app = FastAPI(title="AI 챗봇 서비스", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    https_only=False,       # HTTPS 배포 시 True 권장
    same_site="lax",
    max_age=60 * 60 * 24 * 7,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_exception_handler(_RedirectException, redirect_exception_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """입력 검증 실패를 사용자 친화 메시지로 변환."""
    first = exc.errors()[0] if exc.errors() else {}
    msg = first.get("msg", "입력값이 올바르지 않습니다.")
    logger.info("validation error: path=%s detail=%s", request.url.path, msg)
    return JSONResponse(status_code=422, content={"detail": msg})


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    dur = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        dur,
    )
    return response


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(logs.router)


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    uid = request.session.get("user_id")
    user = db.get(User, uid) if uid else None
    return render(request, "index.html", current_user=user)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "ai_enabled": settings.ai_enabled}
