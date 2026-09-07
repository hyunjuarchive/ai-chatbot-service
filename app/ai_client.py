"""Anthropic Claude API 호출 래퍼.

- API 키가 없으면(mock 모드) 서비스가 죽지 않도록 고정 응답을 돌려준다.
- 타임아웃 / 네트워크 / API 오류는 모두 AIServiceError 로 변환해 상위에서
  "사용자 안내 + 로그" 로 처리하게 한다.
- 문맥 유지: 직전 성공한 Q/A 를 messages 배열로 재구성해 함께 전송한다.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger("chatbot.ai")
settings = get_settings()

SYSTEM_PROMPT = (
    "당신은 한국어로 답하는 친절한 고객 지원 AI 챗봇입니다. "
    "질문이 불명확하면 정중히 되묻고, 모르는 것은 모른다고 말하세요. "
    "답변은 간결하고 실용적으로 작성합니다."
)

# anthropic 패키지가 없거나 키가 없을 때를 대비해 지연 import
try:  # pragma: no cover - import 환경 의존
    import anthropic

    _ANTHROPIC_AVAILABLE = True
except Exception:  # pragma: no cover
    anthropic = None  # type: ignore
    _ANTHROPIC_AVAILABLE = False


class AIServiceError(Exception):
    """AI 호출 실패(타임아웃 포함). 사용자에게는 일반 안내 문구로 노출한다."""


@dataclass
class AIResult:
    answer: str
    latency_ms: int
    mocked: bool


_client = None


def _get_client():
    global _client
    if _client is None:
        kwargs = dict(
            api_key=settings.anthropic_api_key,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,
        )
        if settings.anthropic_base_url.strip():
            kwargs["base_url"] = settings.anthropic_base_url.strip()
        _client = anthropic.Anthropic(**kwargs)
    return _client


def _build_messages(history: list[tuple[str, str]], question: str) -> list[dict]:
    """history: [(question, answer), ...] 오래된 것부터. -> Claude messages 형식."""
    messages: list[dict] = []
    for q, a in history:
        messages.append({"role": "user", "content": q})
        messages.append({"role": "assistant", "content": a})
    messages.append({"role": "user", "content": question})
    return messages


def generate_reply(question: str, history: list[tuple[str, str]] | None = None) -> AIResult:
    history = history or []
    started = time.perf_counter()

    if not settings.ai_enabled or not _ANTHROPIC_AVAILABLE:
        # ---- mock 모드 ----
        latency = int((time.perf_counter() - started) * 1000)
        logger.warning("AI mock mode (no ANTHROPIC_API_KEY). question_len=%d", len(question))
        return AIResult(
            answer=(
                "[테스트 응답] 현재 서버에 AI API 키가 설정되지 않아 예시 답변을 반환합니다. "
                f'질문하신 내용은 "{question[:100]}" 였습니다. '
                ".env 의 ANTHROPIC_API_KEY 를 설정하면 실제 AI 응답이 제공됩니다."
            ),
            latency_ms=latency,
            mocked=True,
        )

    messages = _build_messages(history, question)
    try:
        resp = _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
    except anthropic.APITimeoutError as exc:  # type: ignore[union-attr]
        raise AIServiceError(f"AI 응답 타임아웃({settings.ai_timeout_seconds}s)") from exc
    except anthropic.APIStatusError as exc:  # type: ignore[union-attr]
        raise AIServiceError(f"AI API 오류 status={exc.status_code}") from exc
    except anthropic.APIError as exc:  # type: ignore[union-attr]
        raise AIServiceError(f"AI API 오류: {exc}") from exc
    except Exception as exc:  # 알 수 없는 오류도 서비스가 죽지 않게 흡수
        raise AIServiceError(f"AI 호출 중 알 수 없는 오류: {exc}") from exc

    text = "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    ).strip()
    if not text:
        raise AIServiceError("AI 응답이 비어 있습니다.")

    latency = int((time.perf_counter() - started) * 1000)
    return AIResult(answer=text, latency_ms=latency, mocked=False)
