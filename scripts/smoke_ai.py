"""AI 게이트웨이 실호출 점검 스크립트.

.env 의 ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL / ANTHROPIC_MODEL 을 그대로 사용해
Claude(호환) API 에 한 번 호출하고 응답/에러를 출력한다.

사용:
    python scripts/smoke_ai.py "안녕하세요, 한 문장으로 자기소개 해줘"
"""
from __future__ import annotations

import sys
from pathlib import Path

# Windows 콘솔(cp949)에서도 이모지/한글 출력이 깨지지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai_client import AIServiceError, generate_reply  # noqa: E402
from app.config import get_settings  # noqa: E402

s = get_settings()
prompt = sys.argv[1] if len(sys.argv) > 1 else "한 문장으로 자기소개 해줘."

print(f"base_url : {s.anthropic_base_url or '(공식 Anthropic)'}")
print(f"model    : {s.anthropic_model}")
print(f"ai_enabled(key set): {s.ai_enabled}")
print(f"prompt   : {prompt}\n")

try:
    r = generate_reply(prompt, history=[])
    print(f"OK  mocked={r.mocked}  latency={r.latency_ms}ms")
    print("answer:", r.answer)
except AIServiceError as e:
    print("FAILED:", e)
    sys.exit(1)
