# AI 챗봇 서비스 (FastAPI)

사용자 문의에 실시간으로 응답하는 웹 기반 AI 챗봇. 로그인한 사용자가 웹 페이지에서
질문을 입력하면 서버가 Anthropic Claude API 를 호출해 답변을 생성하고, 모든 대화를
DB 에 누적 저장한다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 문제 정의 | 고객 문의 응대를 사람이 24시간 처리하기 어렵다. 반복 질문에 즉시 답하는 창구가 필요하다. |
| 타겟 사용자 | 서비스/제품에 대해 궁금한 점을 빠르게 묻고 싶은 로그인 사용자, 대화 이력을 확인해야 하는 운영자 |
| 핵심 시나리오 | ① 회원가입/로그인 → ② 채팅 화면에서 질문 입력 → ③ AI 답변 확인 → ④ 내 대화 로그 조회 |

## 2. 기술 스택

- **Backend**: Python 3.12, FastAPI, Uvicorn
- **View**: Jinja2 서버 사이드 템플릿 + 바닐라 JS(fetch)
- **DB**: SQLite + SQLAlchemy 2.0 ORM
- **Auth**: 서명 세션 쿠키(`SessionMiddleware`) + bcrypt 비밀번호 해시
- **AI**: Anthropic Claude API (`anthropic` SDK, 서버에서만 호출)
- **배포**: Docker / Railway / Render

## 3. 시스템 구조

```
[브라우저]
   │  HTML 폼(로그인) · fetch JSON(/api/chat)
   ▼
[FastAPI 앱  app/main.py]
   ├─ SessionMiddleware ............ 세션 쿠키 검증
   ├─ access_log 미들웨어 .......... 모든 요청 로깅
   ├─ routers/auth.py ............. 회원가입·로그인·로그아웃
   ├─ routers/chat.py ............. /api/chat 파이프라인
   │      1) 입력 검증 (schemas.ChatRequest)
   │      2) 최근 Q/A 컨텍스트 조회 (chat_logs)
   │      3) ai_client.generate_reply() ── 타임아웃/예외 처리
   │      4) chat_logs 에 저장 (성공/실패 모두)
   │      5) JSON 응답
   └─ routers/logs.py ............. 내 로그 / 관리자 로그 조회
   ▼
[SQLite  chatbot.db]  users, chat_logs
   ▲
[Anthropic Claude API]  ◀── ai_client.py (서버에서만 키 사용)
```

주요 컴포넌트 역할은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 참고.

## 4. API 명세 (요약)

| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/` | - | 홈 |
| GET/POST | `/register` | - | 회원가입 |
| GET/POST | `/login` | - | 로그인 |
| POST | `/logout` | 세션 | 로그아웃 |
| GET | `/chat` | 세션(페이지) | 채팅 화면 |
| POST | `/api/chat` | 세션(API) | 질문 전송 → AI 응답 |
| GET | `/logs` / `/api/logs` | 세션 | 내 대화 로그 |
| GET | `/admin/logs` / `/api/admin/logs` | 관리자 | 전체 대화 로그 |
| GET | `/healthz` | - | 헬스체크 |

### `POST /api/chat` 예시

요청:
```http
POST /api/chat
Content-Type: application/json
Cookie: session=<로그인 세션>

{ "message": "환불은 며칠 걸리나요?" }
```

성공 응답 `200`:
```json
{
  "answer": "환불은 승인 후 영업일 기준 3~5일 소요됩니다.",
  "log_id": 42,
  "created_at": "2026-09-07T12:34:56.000Z",
  "mocked": false
}
```

검증 실패 `422`:
```json
{ "detail": "빈 질문은 보낼 수 없습니다." }
```

AI 실패/타임아웃 `503` (서비스는 계속 동작):
```json
{ "detail": "AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요." }
```

전체 명세와 더 많은 예시는 [docs/API.md](docs/API.md).

## 5. DB 구조

`users` 1 : N `chat_logs`. ERD 와 필드 설명은 [docs/DB.md](docs/DB.md).

| 테이블 | 핵심 필드 |
|---|---|
| `users` | id, username(unique), password_hash, is_admin, created_at |
| `chat_logs` | id, **user_id**(FK), **created_at**, **question**, **answer**, status(success/error), error_detail, latency_ms |

최소 추적 필드(사용자 식별·생성 시각·질문·응답)를 모두 포함한다.

## 6. 환경 변수

`.env.example` 을 복사해 `.env` 를 만든다. `.env` 는 `.gitignore` 로 커밋 제외된다.

| 키 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | 배포 시 필수 | (없음) | Claude API 키. 없으면 mock 응답 모드 |
| `ANTHROPIC_BASE_URL` | - | (없음) | 서드파티 게이트웨이/프록시로 Claude 사용 시 그 endpoint. 공식 Anthropic 이면 비움 |
| `ANTHROPIC_MODEL` | - | `claude-sonnet-5` | 사용할 모델 ID |
| `AI_TIMEOUT_SECONDS` | - | `30` | AI 호출 타임아웃(초) |
| `AI_MAX_CONTEXT_MESSAGES` | - | `10` | 프롬프트에 포함할 직전 Q/A 개수 |
| `SESSION_SECRET` | 배포 시 필수 | (기본값 있음) | 세션 쿠키 서명 키. 배포 시 랜덤값 교체 |
| `DATABASE_URL` | - | `sqlite:///./chatbot.db` | DB 연결 문자열 |
| `MAX_QUESTION_LENGTH` | - | `2000` | 질문 1건 최대 글자 수 |
| `ADMIN_USERNAMES` | - | `admin` | 관리자 권한 부여할 아이디(콤마 구분) |

```powershell
# SESSION_SECRET 생성 예시
python -c "import secrets; print(secrets.token_hex(32))"
```

## 7. 로컬 실행

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # Windows: Copy-Item .env.example .env
# .env 에 ANTHROPIC_API_KEY 입력 (없으면 mock 응답으로 동작)

uvicorn app.main:app --reload
# http://127.0.0.1:8000
```

테스트:
```bash
pytest -q
```

## 8. 배포

### Railway
1. GitHub 저장소 연결 → `railway.json` 자동 인식(NIXPACKS).
2. Variables 탭에 `ANTHROPIC_API_KEY`, `SESSION_SECRET` 등 환경변수 입력.
3. 배포 후 발급되는 `*.up.railway.app` URL 이 외부 접속 주소.

### Render
1. New → Blueprint → 저장소 선택 → `render.yaml` 자동 적용.
2. `ANTHROPIC_API_KEY` 는 대시보드에서 직접 입력(`sync: false`), `SESSION_SECRET` 은 자동 생성.
3. 발급되는 `*.onrender.com` URL 이 외부 접속 주소.
4. 무료 플랜은 영구 디스크가 없어 재시작 시 SQLite 가 초기화된다. 데이터 유지가 필요하면
   `render.yaml` 의 `disk` 블록을 활성화(유료)한다.

### Docker
```bash
docker build -t ai-chatbot .
docker run -p 8000:8000 --env-file .env ai-chatbot
```

## 9. DB 확인 가이드 (평가자용)

아래 중 편한 방법으로 대화 로그를 확인할 수 있다.

1. **로그 조회 API** — 로그인 후
   `GET /api/logs?limit=50` (내 로그), `GET /api/admin/logs?username=<id>` (관리자)
2. **내부 로그 화면** — `/logs`(내 로그 표), `/admin/logs`(관리자 전체 표)
3. **CLI 스크립트** —
   ```bash
   python scripts/check_db.py            # 요약 + 최근 로그
   python scripts/check_db.py --user alice --limit 50
   ```
4. **직접 SQL** —
   ```bash
   sqlite3 chatbot.db "SELECT id,user_id,created_at,status,substr(question,1,40) FROM chat_logs ORDER BY id DESC LIMIT 20;"
   ```

## 10. 운영/예외 처리

- `POST /api/chat` 처리 중 다음 이벤트가 서버 로그(stdout)에 남는다:
  `request received` → `AI call` → `AI response received` / `AI call failed` → `DB save success` / `DB save failed`
- AI 타임아웃/오류 시 서비스는 죽지 않고 `503` + 안내 문구를 반환하며, `chat_logs` 에
  `status='error'`, `error_detail` 로 원인을 남긴다.
- 입력 검증: 빈 질문 차단, 최대 길이 제한(`MAX_QUESTION_LENGTH`), 아이디 형식/비밀번호 길이 검증.

## 11. 협업 및 형상관리

- 브랜치 전략: `main`(배포) / `develop`(통합) 분리, 기능별 `feature/*` 브랜치 → PR → `develop` 머지.
- 팀 구성원 역할 및 개인별 작업 요약: [docs/TEAM.md](docs/TEAM.md).

## 12. 디렉터리 구조

```
챗봇/
├─ app/
│  ├─ main.py            FastAPI 앱, 미들웨어, 예외 핸들러, / 및 /healthz
│  ├─ config.py          환경변수 설정 (pydantic-settings)
│  ├─ database.py        엔진/세션/Base, init_db()
│  ├─ models.py          User, ChatLog
│  ├─ schemas.py         요청/응답 Pydantic 모델 + 입력 검증
│  ├─ security.py        bcrypt, 세션, 접근 제어 의존성
│  ├─ ai_client.py       Claude API 호출 (타임아웃·예외·mock·컨텍스트)
│  ├─ logging_config.py  stdout 로깅 설정
│  ├─ templates.py       Jinja2 렌더 헬퍼
│  ├─ routers/
│  │  ├─ auth.py         회원가입/로그인/로그아웃
│  │  ├─ chat.py         /chat, /api/chat 파이프라인
│  │  └─ logs.py         /logs, /api/logs, /admin/logs
│  ├─ templates/*.html
│  └─ static/style.css
├─ scripts/check_db.py   평가자용 DB 확인 CLI
├─ tests/test_app.py     통합 테스트 (pytest)
├─ docs/                 ARCHITECTURE / API / DB / TEAM
├─ Dockerfile, .dockerignore, Procfile, railway.json, render.yaml
├─ requirements.txt, .env.example, .gitignore
└─ main.py               루트 진입점 (uvicorn main:app)
```
