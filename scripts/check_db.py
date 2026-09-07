"""평가자용 DB 확인 스크립트.

사용법 (프로젝트 루트에서):
    python scripts/check_db.py            # 요약 + 최근 로그 20건
    python scripts/check_db.py --user kim # 특정 사용자 로그
    python scripts/check_db.py --limit 50

DATABASE_URL 환경변수를 따르며, 기본값은 ./chatbot.db (SQLite) 입니다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.models import ChatLog, User  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", help="username 필터")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    print(f"DB URL: {engine.url}")
    with SessionLocal() as db:
        n_users = db.scalar(select(func.count()).select_from(User)) or 0
        n_logs = db.scalar(select(func.count()).select_from(ChatLog)) or 0
        n_err = db.scalar(
            select(func.count()).select_from(ChatLog).where(ChatLog.status == "error")
        ) or 0
        print(f"users={n_users}  chat_logs={n_logs}  (error={n_err})\n")

        stmt = select(ChatLog).order_by(ChatLog.id.desc()).limit(args.limit)
        if args.user:
            stmt = (
                select(ChatLog)
                .join(User)
                .where(User.username == args.user)
                .order_by(ChatLog.id.desc())
                .limit(args.limit)
            )

        rows = db.scalars(stmt).all()
        for r in rows:
            uname = db.get(User, r.user_id)
            uname = uname.username if uname else f"#{r.user_id}"
            q = r.question.replace("\n", " ")[:60]
            a = (r.answer or "").replace("\n", " ")[:60]
            print(
                f"[{r.id:>4}] {r.created_at:%Y-%m-%d %H:%M:%S} "
                f"{uname:<12} {r.status:<7} "
                f"latency={r.latency_ms}ms\n"
                f"       Q: {q}\n"
                f"       A: {a}"
                + (f"\n       ERR: {r.error_detail}" if r.error_detail else "")
            )


if __name__ == "__main__":
    main()
