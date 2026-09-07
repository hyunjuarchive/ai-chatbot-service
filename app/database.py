"""SQLAlchemy 엔진 / 세션 / Base 정의."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# SQLite 는 기본적으로 스레드 간 커넥션 공유를 막으므로 옵션을 완화한다.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성: 요청당 DB 세션을 열고 종료 시 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """앱 시작 시 테이블을 생성한다 (이미 있으면 무시)."""
    from app import models  # noqa: F401  (모델 등록 목적)

    Base.metadata.create_all(bind=engine)
