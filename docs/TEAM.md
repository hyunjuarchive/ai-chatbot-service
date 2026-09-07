# 팀 구성원 역할 및 개인별 작업 요약

> 아래 표를 팀 상황에 맞게 채우세요. Git 커밋 이력과 크게 모순되지 않도록 작성합니다.
> (미션 요구사항: 팀원별 유의미한 커밋 10회 이상, PR 기반 머지 기록)

## 팀 구성

| 이름 | 역할 | 담당 영역 | 개인별 작업 요약 | 주요 커밋/PR |
|---|---|---|---|---|
| (예) 홍길동 | 팀장 / 백엔드 | FastAPI 앱 구조, `/api/chat` 파이프라인, AI 연동 | `ai_client.py` 타임아웃·예외 처리, 컨텍스트 유지 로직 구현 | #3, #7, #12 |
| (예) 김철수 | 인증 / DB | 회원가입·로그인, 세션, 모델 설계 | `security.py`, `models.py`, `routers/auth.py`, ERD 작성 | #2, #5, #9 |
| (예) 이영희 | 프론트 / 로그 | 템플릿·CSS, 로그 조회 화면/ API | `templates/*`, `routers/logs.py`, `scripts/check_db.py` | #4, #8, #11 |
| (예) 박민수 | 배포 / 문서 | Docker, Railway/Render 설정, README | `Dockerfile`, `render.yaml`, `docs/`, CI 점검 | #1, #6, #10 |

## 브랜치 전략

- `main` : 배포 가능한 상태만 유지. 태그로 릴리스 관리.
- `develop` : 기능 통합 브랜치. 모든 `feature/*` PR 의 머지 대상.
- `feature/<이슈번호>-<요약>` : 기능 단위 작업 브랜치. 예) `feature/12-ai-timeout`
- 흐름: 이슈 생성 → `feature/*` 분기 → 작업/커밋 → `develop` 로 PR → 리뷰 1인 이상 승인 → Squash/Merge
- 배포: `develop` → `main` PR → 머지 시 배포 트리거

## PR 규칙

- 제목: `[영역] 요약` (예: `[chat] AI 호출 타임아웃 처리`)
- 본문: 변경 요약 / 테스트 방법 / 관련 이슈
- 최소 1인 리뷰 승인 후 머지, `develop` 직접 push 금지

## 커밋 컨벤션 (권장)

```
feat: 사용자에게 보이는 기능 추가
fix:  버그 수정
docs: 문서
refactor: 동작 변화 없는 리팩터링
test: 테스트 추가/수정
chore: 빌드/설정
```
