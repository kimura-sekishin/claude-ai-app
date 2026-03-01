import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from app.models.debate import (
    DEFAULT_PERSONA_A,
    DEFAULT_PERSONA_B,
    DebateConfig,
    DebateStartRequest,
    DebateStartResponse,
    Persona,
    PersonaInput,
)
from app.models.errors import SessionNotFoundError
from app.services.debate_formatter import format_debate_as_markdown
from app.services.debate_service import DebateService

router = APIRouter(prefix="/api/debate", tags=["debate"])

# デフォルトのDebateServiceインスタンス（モジュールロード時に1度だけ作成）
_debate_service = DebateService()

# SSEイベントの最大待機時間（秒）
_SSE_TIMEOUT_SECONDS = 300.0


def _to_persona(inp: PersonaInput, default: Persona) -> Persona:
    """PersonaInputをPersonaに変換する。空欄はデフォルト値で補完する。"""
    return Persona(
        name=inp.name.strip() or default.name,
        description=inp.description.strip() or default.description,
    )


@router.post("/start", response_model=DebateStartResponse)
async def start_debate(request: DebateStartRequest) -> DebateStartResponse:
    """議論セッションを開始し、session_id を返す。"""
    config = DebateConfig(
        persona_a=_to_persona(request.persona_a, DEFAULT_PERSONA_A),
        persona_b=_to_persona(request.persona_b, DEFAULT_PERSONA_B),
        theme=request.theme,
        max_turns=request.max_turns,
    )
    session_id, _ = _debate_service.create_and_start(config)
    return DebateStartResponse(session_id=session_id)


@router.get("/{session_id}/stream")
async def stream_debate(session_id: str) -> EventSourceResponse:
    """SSE でリアルタイムに議論イベントを配信する。"""
    try:
        queue = _debate_service.get_stream_queue(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        try:
            while True:
                try:
                    event: dict[str, object] = await asyncio.wait_for(
                        queue.get(), timeout=_SSE_TIMEOUT_SECONDS
                    )
                except TimeoutError:
                    timeout_event = {"type": "error", "message": "タイムアウトしました"}
                    yield {"data": json.dumps(timeout_event, ensure_ascii=False)}
                    break
                yield {"data": json.dumps(event, ensure_ascii=False)}
                if event.get("type") in ("complete", "error"):
                    break
        finally:
            # ストリーム終了後にキューを解放（セッションはエクスポート用に保持）
            _debate_service.release_queue(session_id)

    return EventSourceResponse(event_generator())


@router.get("/{session_id}/export")
async def export_debate(session_id: str) -> Response:
    """議論セッションをMarkdownファイルとしてダウンロードする。"""
    try:
        session = _debate_service.get_session_for_export(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    content = format_debate_as_markdown(session)
    filename = f"debate-{session_id[:8]}.md"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
