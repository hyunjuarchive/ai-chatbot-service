"""루트 진입점.

로컬 실행:
    uvicorn main:app --reload
또는:
    python main.py
"""
from app.main import app

if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("RELOAD", "")),
    )
