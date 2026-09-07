"""공용 Jinja2 템플릿 인스턴스와 렌더 헬퍼."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.models import User

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render(
    request: Request,
    name: str,
    context: dict[str, Any] | None = None,
    *,
    current_user: User | None = None,
    status_code: int = 200,
):
    ctx: dict[str, Any] = {"current_user": current_user}
    if context:
        ctx.update(context)
    return templates.TemplateResponse(
        request=request, name=name, context=ctx, status_code=status_code
    )
