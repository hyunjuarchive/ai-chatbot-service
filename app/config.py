"""애플리케이션 설정. 모든 값은 환경변수(.env)에서 읽는다."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- AI ---
    # 인증: 공식 Anthropic 은 api_key(x-api-key 헤더),
    #       게이트웨이(LiteLLM 등)는 보통 auth_token(Authorization: Bearer 헤더)을 쓴다.
    anthropic_api_key: str = ""
    anthropic_auth_token: str = ""
    # 서드파티 게이트웨이/프록시를 쓸 때만 설정. 비우면 공식 Anthropic 엔드포인트 사용.
    anthropic_base_url: str = ""
    anthropic_model: str = "claude-sonnet-5"
    ai_timeout_seconds: float = 30.0
    ai_max_context_messages: int = 10

    # --- 보안 / 세션 ---
    session_secret: str = "change-me-to-a-long-random-string"

    # --- DB ---
    database_url: str = "sqlite:///./chatbot.db"

    # --- 입력 검증 ---
    max_question_length: int = 2000

    # --- 관리자 ---
    admin_usernames: str = "admin"

    @property
    def admin_username_set(self) -> set[str]:
        return {u.strip() for u in self.admin_usernames.split(",") if u.strip()}

    @property
    def ai_enabled(self) -> bool:
        """API 키 또는 인증 토큰이 있으면 True, 둘 다 없으면 mock 모드."""
        return bool(self.anthropic_api_key.strip() or self.anthropic_auth_token.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
