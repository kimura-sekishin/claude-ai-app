import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infra import session_store
from app.models.debate import DebateConfig, DebateStatus, Persona
from app.services.debate_service import DebateService


def _make_config() -> DebateConfig:
    return DebateConfig(
        persona_a=Persona(name="楽観コンサル", description="AI投資に積極的"),
        persona_b=Persona(name="慎重アナリスト", description="リスク重視"),
        theme="AIへの投資はすべきか",
        max_turns=1,
    )


@pytest.fixture(autouse=True)
def cleanup_store() -> object:
    """各テスト後にストアをクリアする。"""
    yield
    session_store._sessions.clear()
    session_store._event_queues.clear()


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """AsyncMockで debate を即完了するモックオーケストレーターを返す。"""
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value=None)
    return orchestrator


class TestDebateServiceCreateAndStart:
    async def test_正常系_session_idとキューが返される(
        self, mock_orchestrator: MagicMock
    ) -> None:
        # Given
        service = DebateService(orchestrator=mock_orchestrator)
        config = _make_config()

        # When
        session_id, queue = service.create_and_start(config)

        # Then
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID形式
        assert queue is not None

    async def test_正常系_セッションがストアに登録される(
        self, mock_orchestrator: MagicMock
    ) -> None:
        # Given
        service = DebateService(orchestrator=mock_orchestrator)
        config = _make_config()

        # When
        session_id, _ = service.create_and_start(config)

        # Then
        session = session_store.get_session(session_id)
        assert session.session_id == session_id
        assert session.status == DebateStatus.RUNNING

    async def test_正常系_orchestratorのrunが呼ばれる(
        self, mock_orchestrator: MagicMock
    ) -> None:
        # Given
        service = DebateService(orchestrator=mock_orchestrator)
        config = _make_config()

        # When
        service.create_and_start(config)
        # バックグラウンドタスクが実行されるのを待つ
        await asyncio.sleep(0)

        # Then
        mock_orchestrator.run.assert_called_once()

    async def test_正常系_DIなしでデフォルトオーケストレーターが生成される(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Given: 環境変数を設定してデフォルト生成を試みる
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")

        with (
            patch("app.services.debate_orchestrator.AgentRunner"),
            patch("app.services.debate_orchestrator.anthropic.AsyncAnthropicBedrock"),
        ):
            service = DebateService()

        # Then: インスタンスが正常に生成される
        assert service._orchestrator is not None


class TestDebateServiceGetStreamQueue:
    async def test_正常系_存在するセッションのキューを取得できる(
        self, mock_orchestrator: MagicMock
    ) -> None:
        # Given
        service = DebateService(orchestrator=mock_orchestrator)
        config = _make_config()
        session_id, original_queue = service.create_and_start(config)

        # When
        queue = service.get_stream_queue(session_id)

        # Then
        assert queue is original_queue

    async def test_異常系_存在しないsession_idでSessionNotFoundError(
        self, mock_orchestrator: MagicMock
    ) -> None:
        # Given
        service = DebateService(orchestrator=mock_orchestrator)
        from app.models.errors import SessionNotFoundError

        # When / Then
        with pytest.raises(SessionNotFoundError):
            service.get_stream_queue("non-existent-id")


class TestDebateServiceReleaseQueue:
    async def test_正常系_キューが解放されセッションは保持される(
        self, mock_orchestrator: MagicMock
    ) -> None:
        # Given
        service = DebateService(orchestrator=mock_orchestrator)
        config = _make_config()
        session_id, _ = service.create_and_start(config)

        # When
        service.release_queue(session_id)

        # Then: セッション本体は残っている
        session = session_store.get_session(session_id)
        assert session.session_id == session_id
