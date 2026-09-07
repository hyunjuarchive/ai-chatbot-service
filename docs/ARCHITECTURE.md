# 시스템 아키텍처

## 개요

단일 FastAPI 프로세스가 웹 UI(서버 렌더링)와 JSON API 를 함께 제공한다.
상태는 SQLite 한 파일에 저장하고, AI 응답 생성만 외부(Anthropic Claude API)에 위임한다.

```
                 ┌─────────────────────────────────────────────┐
   HTTPS         │                FastAPI (app.main:app)        │
 ┌───────┐       │                                             │
 │Browser│──────▶│ SessionMiddleware ─ 세션 쿠키(서명) 검증      │
 └───────┘       │        │                                     │
                 │        ▼                                     │
                 │ access_log 미들웨어 ─ method/path/status/ms   │
                 │        │                                     │
                 │        ▼                                     │
                 │  ┌── auth.py ── users 테이블 (회원가입/로그인) │
                 │  ├── chat.py ── /api/chat 파이프라인          │
                 │  └── logs.py ── chat_logs 조회 (내/관리자)     │
                 │        │                    │                │
                 └────────┼────────────────────┼────────────────┘
                          ▼                    ▼
                   ┌────────────┐      ┌──────────────────┐
                   │ SQLite     │      │ Anthropic Claude │
                   │ chatbot.db │      │ API (서버 호출)   │
                   └────────────┘      └──────────────────┘
```

## 요청 파이프라인: `POST /api/chat`

```
1. 인증          require_user_api  → 세션에 user_id 없으면 401
2. 입력 검증      schemas.ChatRequest
                 - message 공백/누락 → 422
                 - 길이 > MAX_QUESTION_LENGTH → 422
3. 컨텍스트 구성  chat.py _recent_history()
                 - 같은 user_id, status='success' 인 최근 N(=AI_MAX_CONTEXT_MESSAGES)건
                 - 오래된 순으로 (user, assistant) 메시지쌍 재구성
4. AI 호출        ai_client.generate_reply(question, history)
                 - anthropic.Anthropic(timeout=AI_TIMEOUT_SECONDS, max_retries=1)
                 - APITimeoutError / APIStatusError / APIError / 그 외 예외
                   → 전부 AIServiceError 로 변환
                 - 키 없으면 mock 응답 반환 (mocked=True)
5. 로그 저장      chat_logs INSERT
                 - 성공: status='success', answer, latency_ms
                 - 실패: status='error', error_detail  (4에서 예외 시)
                 - 저장 실패해도 사용자에겐 답변 반환 (best-effort)
6. 응답          200 {answer, log_id, created_at, mocked}
                 또는 503 {detail: 사용자 안내문}  (AI 실패 시)
```

## 컴포넌트 역할

| 파일 | 역할 |
|---|---|
| `app/main.py` | 앱 생성, 미들웨어 등록(Session, access_log), 예외 핸들러(리다이렉트, 검증), 라우터 포함, `/`·`/healthz`, `lifespan` 에서 `init_db()` |
| `app/config.py` | `.env` → `Settings` (pydantic-settings). `ai_enabled`, `admin_username_set` 파생 속성 |
| `app/database.py` | SQLAlchemy 엔진/세션, `get_db` 의존성, `init_db()`(create_all) |
| `app/models.py` | `User`, `ChatLog` ORM 모델 |
| `app/schemas.py` | `ChatRequest`(입력 검증), `ChatResponse`, 로그 응답 스키마 |
| `app/security.py` | bcrypt 해시/검증, 세션 로그인/로그아웃, `get_current_user`·`require_user_api`·`require_user_page`·`require_admin` |
| `app/ai_client.py` | Claude 호출 캡슐화. 타임아웃/예외 → `AIServiceError`, mock 폴백, 컨텍스트 메시지 빌드 |
| `app/routers/auth.py` | `/register`, `/login`, `/logout` (HTML 폼) |
| `app/routers/chat.py` | `/chat`(화면), `/api/chat`(파이프라인), `_save_log` |
| `app/routers/logs.py` | `/api/logs`, `/logs`, `/api/admin/logs`, `/admin/logs` |
| `app/logging_config.py` | stdout 스트림 핸들러 + 공통 포맷 |
| `scripts/check_db.py` | 평가자용 DB 요약/로그 덤프 CLI |

## 인증 / 접근 제어

- 로그인 시 `request.session["user_id"]` 저장 → 서명된 쿠키로 왕복.
- **비로그인 상태 구분**: 페이지(`require_user_page`)는 `/login` 으로 303 리다이렉트,
  API(`require_user_api`)는 401 JSON.
- 챗봇 질문/응답(`/api/chat`, `/chat`)은 로그인 사용자 전용.
- 관리자 화면/조회는 `is_admin` (가입 시 `ADMIN_USERNAMES` 목록이면 자동 부여).

## 장애 격리

- AI 호출부는 모든 예외를 `AIServiceError` 로 좁혀 상위에서 단일 처리.
- DB 저장 실패는 `try/except + rollback` 후 로그만 남기고 사용자 응답은 유지.
- `lifespan` 에서 기본 `SESSION_SECRET`/키 미설정 시 경고 로그.
