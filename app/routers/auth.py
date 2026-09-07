"""회원가입 / 로그인 / 로그아웃 라우트 (HTML 폼 기반)."""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.security import (
    get_current_user,
    hash_password,
    login_user,
    logout_user,
    verify_password,
)
from app.templates import render

logger = logging.getLogger("chatbot.auth")
router = APIRouter(tags=["auth"])
settings = get_settings()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
PASSWORD_MIN = 8
PASSWORD_MAX = 64


def _validate(username: str, password: str) -> str | None:
    """입력 검증. 문제가 있으면 오류 메시지를, 없으면 None 을 반환."""
    if not USERNAME_RE.match(username):
        return "아이디는 영문/숫자/밑줄 3~20자여야 합니다."
    if not (PASSWORD_MIN <= len(password) <= PASSWORD_MAX):
        return f"비밀번호는 {PASSWORD_MIN}~{PASSWORD_MAX}자여야 합니다."
    return None


@router.get("/register")
def register_form(request: Request, user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/chat", status_code=status.HTTP_303_SEE_OTHER)
    return render(request, "register.html", {"error": None}, current_user=None)


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()
    err = _validate(username, password)
    if err:
        return render(request, "register.html", {"error": err}, status_code=400)

    exists = db.scalar(select(User).where(User.username == username))
    if exists:
        return render(
            request, "register.html", {"error": "이미 존재하는 아이디입니다."}, status_code=400
        )

    user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=username in settings.admin_username_set,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    login_user(request, user)
    logger.info("user registered: id=%s username=%s admin=%s", user.id, user.username, user.is_admin)
    return RedirectResponse("/chat", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login")
def login_form(
    request: Request,
    next: str = "/chat",
    user: User | None = Depends(get_current_user),
):
    if user:
        return RedirectResponse("/chat", status_code=status.HTTP_303_SEE_OTHER)
    return render(request, "login.html", {"error": None, "next": next}, current_user=None)


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/chat"),
    db: Session = Depends(get_db),
):
    username = username.strip()
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        logger.warning("login failed: username=%s", username)
        return render(
            request,
            "login.html",
            {"error": "아이디 또는 비밀번호가 올바르지 않습니다.", "next": next},
            status_code=401,
        )
    login_user(request, user)
    logger.info("login success: id=%s username=%s", user.id, user.username)
    safe_next = next if next.startswith("/") else "/chat"
    return RedirectResponse(safe_next, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
