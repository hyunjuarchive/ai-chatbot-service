# API 명세

Base URL: 로컬 `http://127.0.0.1:8000` / 배포 시 발급된 서비스 URL

인증은 로그인 시 발급되는 **세션 쿠키**로 이루어진다. 브라우저는 자동 전송되며,
`curl` 사용 시 `-c cookies.txt -b cookies.txt` 로 쿠키를 저장/재사용한다.

---

## 인증

### `POST /register`
회원가입 후 자동 로그인. `application/x-www-form-urlencoded`.

| 필드 | 규칙 |
|---|---|
| `username` | 영문/숫자/밑줄 3~20자 |
| `password` | 8~64자 |

- 성공: `303` → `/chat`
- 검증 실패 / 중복 아이디: `400` (회원가입 페이지 재렌더, 오류 메시지 표시)

```bash
curl -i -c cookies.txt -X POST http://127.0.0.1:8000/register \
  -d "username=alice&password=password123"
```

### `POST /login`
| 필드 | |
|---|---|
| `username` | |
| `password` | |
| `next` | (선택) 로그인 후 이동 경로, 내부 경로만 허용 |

- 성공: `303` → `next`(기본 `/chat`)
- 실패: `401` (로그인 페이지 재렌더)

```bash
curl -i -c cookies.txt -b cookies.txt -X POST http://127.0.0.1:8000/login \
  -d "username=alice&password=password123"
```

### `POST /logout`
세션 삭제 후 `303` → `/`.

---

## 챗봇

### `POST /api/chat`
로그인 필요. `application/json`.

요청 body:
```json
{ "message": "환불은 며칠 걸리나요?" }
```

| 필드 | 타입 | 규칙 |
|---|---|---|
| `message` | string | 1자 이상, `MAX_QUESTION_LENGTH`(기본 2000) 이하, 공백만이면 거부 |

응답 `200`:
```json
{
  "answer": "환불은 승인 후 영업일 기준 3~5일 소요됩니다.",
  "log_id": 42,
  "created_at": "2026-09-07T12:34:56.123456+00:00",
  "mocked": false
}
```
- `mocked`: `true` 이면 서버에 `ANTHROPIC_API_KEY` 가 없어 예시 답변을 반환한 것.

오류 응답:

| 상태 | body | 상황 |
|---|---|---|
| `401` | `{"detail": "로그인이 필요합니다."}` | 미로그인 |
| `422` | `{"detail": "빈 질문은 보낼 수 없습니다."}` | 공백 입력 |
| `422` | `{"detail": "String should have at most 2000 characters"}` | 길이 초과 |
| `503` | `{"detail": "AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."}` | AI 타임아웃/오류 (로그엔 `status='error'` 저장) |

```bash
curl -i -b cookies.txt -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"안녕하세요"}'
```

**문맥 유지**: 서버는 같은 사용자의 최근 성공 Q/A `AI_MAX_CONTEXT_MESSAGES`건(기본 10)을
프롬프트에 포함한다. 클라이언트는 이전 대화를 다시 보낼 필요가 없다.

### `GET /chat`
로그인 필요. 채팅 화면(HTML). 미로그인 시 `/login?next=/chat` 로 리다이렉트.

---

## 로그 조회

### `GET /api/logs`
로그인 사용자 본인의 대화 로그.

| 쿼리 | 기본 | 범위 |
|---|---|---|
| `limit` | 50 | 1~200 |
| `offset` | 0 | ≥0 |

응답:
```json
{
  "total": 3,
  "items": [
    {
      "id": 42,
      "question": "환불은 며칠 걸리나요?",
      "answer": "환불은 ...",
      "status": "success",
      "error_detail": null,
      "latency_ms": 812,
      "created_at": "2026-09-07T12:34:56.123456+00:00"
    }
  ]
}
```

```bash
curl -b cookies.txt "http://127.0.0.1:8000/api/logs?limit=20"
```

### `GET /api/admin/logs`
관리자(`is_admin`) 전용. 미관리자는 `403`.

| 쿼리 | 설명 |
|---|---|
| `username` | 특정 사용자 로그만 필터 |
| `limit` | 기본 100, 1~500 |
| `offset` | 기본 0 |

```bash
curl -b cookies.txt "http://127.0.0.1:8000/api/admin/logs?username=alice"
```

### `GET /logs` · `GET /admin/logs`
같은 데이터의 HTML 표 화면.

---

## 기타

### `GET /healthz`
```json
{ "status": "ok", "ai_enabled": true }
```

### 대화형 문서
FastAPI 자동 문서: `GET /docs` (Swagger UI), `GET /redoc`.
