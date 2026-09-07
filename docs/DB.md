# 데이터베이스 구조

- 엔진: SQLite (`DATABASE_URL`, 기본 `sqlite:///./chatbot.db`)
- ORM: SQLAlchemy 2.0 (`app/models.py`)
- 스키마 생성: 앱 시작 시 `init_db()` → `Base.metadata.create_all()`

## ERD

```
┌───────────────────────────┐          ┌────────────────────────────────────┐
│           users           │          │             chat_logs              │
├───────────────────────────┤          ├────────────────────────────────────┤
│ id            INTEGER PK  │ 1      N │ id            INTEGER PK           │
│ username      VARCHAR(50) │──────────│ user_id       INTEGER FK→users.id  │
│               UNIQUE      │          │ question      TEXT      NOT NULL    │
│ password_hash VARCHAR(255)│          │ answer        TEXT      NOT NULL(=''):
│ is_admin      BOOLEAN     │          │ status        VARCHAR(20) 'success' │
│ created_at    DATETIME    │          │                / 'error'           │
└───────────────────────────┘          │ error_detail  TEXT      NULL       │
                                       │ latency_ms    INTEGER   NULL       │
                                       │ created_at    DATETIME  NOT NULL   │
                                       └────────────────────────────────────┘
       관계: users.id  1 ──< chat_logs.user_id   (ON DELETE CASCADE)
```

## 테이블: `users`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | INTEGER | PK, auto | 사용자 식별자 |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 로그인 아이디 |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt 해시 (평문 저장 안 함) |
| `is_admin` | BOOLEAN | NOT NULL, default false | 관리자 여부. 가입 시 `ADMIN_USERNAMES` 이면 true |
| `created_at` | DATETIME(tz) | NOT NULL, default now(UTC) | 가입 시각 |

## 테이블: `chat_logs`

대화 1턴(질문 + 응답)당 1행. 성공/실패 모두 기록한다.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | INTEGER | PK, auto | 로그 식별자 |
| `user_id` | INTEGER | FK→`users.id`, NOT NULL, INDEX, ON DELETE CASCADE | **사용자 식별** |
| `question` | TEXT | NOT NULL | **사용자 질문** (검증 후 저장) |
| `answer` | TEXT | NOT NULL, default `''` | **AI 응답**. 실패 시 빈 문자열 |
| `status` | VARCHAR(20) | NOT NULL, default `'success'` | `success` \| `error` |
| `error_detail` | TEXT | NULL | 실패 원인(타임아웃/HTTP status 등). 원인 추적용 |
| `latency_ms` | INTEGER | NULL | AI 호출 소요 시간(ms) |
| `created_at` | DATETIME(tz) | NOT NULL, INDEX, default now(UTC) | **생성 시각** |

> 미션 최소 추적 필드(사용자 식별 · 생성 시각 · 질문 · 응답)를 모두 만족.

## 자주 쓰는 조회

```sql
-- 특정 사용자의 최근 대화
SELECT c.id, c.created_at, c.status, c.latency_ms, c.question, c.answer
FROM chat_logs c JOIN users u ON u.id = c.user_id
WHERE u.username = 'alice'
ORDER BY c.id DESC LIMIT 20;

-- 실패한 호출만 (원인 추적)
SELECT id, user_id, created_at, error_detail
FROM chat_logs WHERE status = 'error' ORDER BY id DESC;

-- 사용자별 대화 수
SELECT u.username, COUNT(*) AS n
FROM chat_logs c JOIN users u ON u.id = c.user_id
GROUP BY u.username ORDER BY n DESC;
```

## 확인 방법

- CLI: `python scripts/check_db.py [--user <id>] [--limit N]`
- API: `GET /api/logs`, `GET /api/admin/logs`
- 화면: `/logs`, `/admin/logs`
- 직접: `sqlite3 chatbot.db "SELECT * FROM chat_logs ORDER BY id DESC LIMIT 10;"`
