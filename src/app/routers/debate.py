import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.infra import session_store
from app.models.debate import (
    DEFAULT_PERSONA_A,
    DEFAULT_PERSONA_B,
    DebateConfig,
    DebateSession,
    DebateStartRequest,
    DebateStartResponse,
    DebateStatus,
    Persona,
    PersonaInput,
)
from app.models.errors import SessionNotFoundError
from app.services.debate_orchestrator import DebateOrchestrator

router = APIRouter(prefix="/api/debate", tags=["debate"])


def _to_persona(inp: PersonaInput, default: Persona) -> Persona:
    """PersonaInputをPersonaに変換する。空欄はデフォルト値で補完する。"""
    return Persona(
        name=inp.name.strip() or default.name,
        description=inp.description.strip() or default.description,
    )


# バックグラウンドタスクへの参照を保持（GCによる早期破棄を防ぐ）
_background_tasks: set[asyncio.Task[None]] = set()

# SSEイベントの最大待機時間（秒）
_SSE_TIMEOUT_SECONDS = 300.0


@router.post("/start", response_model=DebateStartResponse)
async def start_debate(request: DebateStartRequest) -> DebateStartResponse:
    """議論セッションを開始し、session_id を返す。"""
    session_id = str(uuid.uuid4())

    config = DebateConfig(
        persona_a=_to_persona(request.persona_a, DEFAULT_PERSONA_A),
        persona_b=_to_persona(request.persona_b, DEFAULT_PERSONA_B),
        theme=request.theme,
    )
    session = DebateSession(
        session_id=session_id,
        config=config,
        status=DebateStatus.RUNNING,
    )
    queue = session_store.create_session(session)

    orchestrator = DebateOrchestrator()
    task = asyncio.create_task(
        orchestrator.run(config=config, event_queue=queue, session=session)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return DebateStartResponse(session_id=session_id)


@router.get("/{session_id}/stream")
async def stream_debate(session_id: str) -> EventSourceResponse:
    """SSE でリアルタイムに議論イベントを配信する。"""
    try:
        session_store.get_session(session_id)
        queue = session_store.get_queue(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    async def event_generator() -> AsyncIterator[dict[str, str]]:
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

    return EventSourceResponse(event_generator())
