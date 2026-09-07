"""비밀번호 해시 + 세션 기반 현재 사용자 조회 / 접근 제어 의존성."""
from __future__ import annotations

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

SESSION_USER_KEY = "user_id"
_BCRYPT_MAX_BYTES = 72  # bcrypt 는 72바이트까지만 사용한다.


def hash_password(plain: str) -> str:
    pw = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except ValueError:
        return False


def login_user(request: Request, user: User) -> None:
    request.session[SESSION_USER_KEY] = user.id


def logout_user(request: Request) -> None:
    request.session.pop(SESSION_USER_KEY, None)


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """로그인 상태면 User, 아니면 None. (접근 제어를 강제하지 않는 조회용)"""
    user_id = request.session.get(SESSION_USER_KEY)
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user_page(
    request: Request, user: User | None = Depends(get_current_user)
) -> User:
    """HTML 페이지용: 미로그인 시 /login 으로 리다이렉트."""
    if user is None:
        raise _RedirectException("/login?next=" + request.url.path)
    return user


def require_user_api(user: User | None = Depends(get_current_user)) -> User:
    """API용: 미로그인 시 401 JSON."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
        )
    return user


def require_admin(user: User = Depends(require_user_api)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다."
        )
    return user


class _RedirectException(Exception):
    """페이지 접근 제어용 리다이렉트 신호. main.py 의 예외 핸들러가 처리한다."""

    def __init__(self, location: str) -> None:
        self.location = location
        super().__init__(location)


def redirect_exception_handler(request: Request, exc: _RedirectException):
    return RedirectResponse(url=exc.location, status_code=status.HTTP_303_SEE_OTHER)
