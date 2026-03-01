import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.routers import debate  # noqa: E402

app = FastAPI(title="AI討論 / AI Debate", version="0.1.0")

app.include_router(debate.router)

# 静的ファイル配信（フロントエンド）
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
