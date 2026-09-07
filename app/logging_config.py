"""표준 logging 설정. 모든 로그는 stdout 으로 나가 배포 플랫폼이 수집한다."""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # 우리 앱 로거 네임스페이스
    logging.getLogger("chatbot").setLevel(level)
    # uvicorn 액세스 로그는 그대로 두되 포맷 통일
    logging.getLogger("uvicorn.access").handlers = [handler]

    _CONFIGURED = True
