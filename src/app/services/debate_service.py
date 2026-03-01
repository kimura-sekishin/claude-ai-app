from __future__ import annotations

import asyncio
import uuid

from app.infra import session_store
from app.models.debate import (
    DebateConfig,
    DebateEventQueue,
    DebateSession,
    DebateStatus,
)
from app.services.debate_orchestrator import DebateOrchestrator

# バックグラウンドタスクへの参照を保持（GCによる早期破棄を防ぐ）
_background_tasks: set[asyncio.Task[None]] = set()


class DebateService:
    """議論セッションのライフサイクルを管理するサービス。

    routers/ がインフラ層（session_store）に直接依存しないよう、
    セッション管理・議論開始・ストリーム取得・エクスポート取得を一元化する。
    """

    def __init__(self, orchestrator: DebateOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator or DebateOrchestrator()

    def create_and_start(self, config: DebateConfig) -> tuple[str, DebateEventQueue]:
        """セッションを作成し、バックグラウンドで議論を開始する。

        Args:
            config: 議論設定（ペルソナ・テーマ・ターン数）

        Returns:
            (session_id, event_queue) のタプル
        """
        session_id = str(uuid.uuid4())
        session = DebateSession(
            session_id=session_id,
            config=config,
            status=DebateStatus.RUNNING,
        )
        queue = session_store.create_session(session)

        task = asyncio.create_task(
            self._orchestrator.run(config=config, event_queue=queue, session=session)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        return session_id, queue

    def get_stream_queue(self, session_id: str) -> DebateEventQueue:
        """SSEストリーム用のイベントキューを取得する。

        Raises:
            SessionNotFoundError: セッションが見つからない場合
        """
        session_store.get_session(session_id)  # 存在確認
        return session_store.get_queue(session_id)

    def get_session_for_export(self, session_id: str) -> DebateSession:
        """エクスポート用のセッションを取得する。

        Raises:
            SessionNotFoundError: セッションが見つからない場合
        """
        return session_store.get_session(session_id)

    def release_queue(self, session_id: str) -> None:
        """SSEストリーム終了後にイベントキューを解放する。

        セッション本体（DebateSession）はエクスポート用に保持する。
        """
        session_store.delete_queue(session_id)
