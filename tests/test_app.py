"""통합 테스트. 임시 SQLite 파일 DB 로 전체 파이프라인을 검증한다.

실행:  pytest -q
"""
from __future__ import annotations

import os
import tempfile

import pytest

# 앱 import 전에 환경변수로 임시 DB 지정 (실 서비스 DB 오염 방지)
_TMP_DB = os.path.join(tempfile.gettempdir(), "chatbot_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["ANTHROPIC_API_KEY"] = ""          # mock 모드 강제
os.environ["SESSION_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:  # with 블록에서 lifespan 실행 → 테이블 생성
        yield c


def _register(client, username="alice", password="password123"):
    return client.post(
        "/register",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_health(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_requires_login(client):
    r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 401


def test_chat_page_redirects_when_anonymous(client):
    r = client.get("/chat", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_register_and_chat_pipeline(client):
    r = _register(client)
    assert r.status_code == 303

    r = client.post("/api/chat", json={"message": "안녕하세요, 반가워요"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["mocked"] is True
    assert body["log_id"] > 0

    # 로그가 사용자 기준으로 조회된다
    r = client.get("/api/logs")
    assert r.status_code == 200
    logs = r.json()
    assert logs["total"] == 1
    assert logs["items"][0]["question"] == "안녕하세요, 반가워요"
    assert logs["items"][0]["status"] == "success"


def test_input_validation_blank(client):
    _register(client, username="bob")
    r = client.post("/api/chat", json={"message": "   "})
    assert r.status_code == 422


def test_input_validation_too_long(client):
    _register(client, username="carol")
    r = client.post("/api/chat", json={"message": "x" * 9999})
    assert r.status_code == 422


def test_duplicate_username_rejected(client):
    _register(client, username="dave")
    client.cookies.clear()
    r = _register(client, username="dave")
    assert r.status_code == 400


def test_wrong_password_rejected(client):
    _register(client, username="erin", password="password123")
    client.cookies.clear()
    r = client.post(
        "/login",
        data={"username": "erin", "password": "wrongpass"},
        follow_redirects=False,
    )
    assert r.status_code == 401


def test_admin_logs_forbidden_for_normal_user(client):
    _register(client, username="frank")
    r = client.get("/api/admin/logs")
    assert r.status_code == 403


def test_ai_failure_is_logged_and_handled(client, monkeypatch):
    """AI 호출이 실패해도 500 이 아니라 503 + 안내가 반환되고 error 로그가 쌓인다."""
    _register(client, username="grace")

    from app import ai_client

    def boom(*_a, **_kw):
        raise ai_client.AIServiceError("타임아웃 시뮬레이션")

    monkeypatch.setattr(ai_client, "generate_reply", boom)
    # chat 라우터는 import 시점에 이름을 바인딩하므로 그쪽도 교체
    from app.routers import chat as chat_router

    monkeypatch.setattr(chat_router, "generate_reply", boom)

    r = client.post("/api/chat", json={"message": "이건 실패할 거예요"})
    assert r.status_code == 503
    assert "잠시 후" in r.json()["detail"]

    r = client.get("/api/logs")
    items = r.json()["items"]
    assert items[0]["status"] == "error"
    assert items[0]["error_detail"]
