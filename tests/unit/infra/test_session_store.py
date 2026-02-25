import asyncio

import pytest

from app.infra import session_store
from app.models.debate import (
    DebateConfig,
    DebateSession,
    DebateStatus,
    Persona,
)
from app.models.errors import SessionNotFoundError


def _make_session(session_id: str = "test-session-id") -> DebateSession:
    return DebateSession(
        session_id=session_id,
        config=DebateConfig(
            persona_a=Persona(name="ペルソナA", description="楽観的な立場"),
            persona_b=Persona(name="ペルソナB", description="慎重な立場"),
            theme="AIへの投資はすべきか",
        ),
        status=DebateStatus.RUNNING,
    )


@pytest.fixture(autouse=True)
def cleanup_store() -> object:
    """各テスト後にストアをクリアする。"""
    yield
    session_store._sessions.clear()
    session_store._event_queues.clear()


class TestCreateSession:
    def test_セッションが保存されてキューが返される(self) -> None:
        # Given
        session = _make_session()

        # When
        queue = session_store.create_session(session)

        # Then
        assert isinstance(queue, asyncio.Queue)
        assert session_store._sessions["test-session-id"] is session
        assert session_store._event_queues["test-session-id"] is queue


class TestGetSession:
    def test_正常系_DebateSessionが返される(self) -> None:
        # Given
        session = _make_session()
        session_store.create_session(session)

        # When
        result = session_store.get_session("test-session-id")

        # Then
        assert result is session

    def test_異常系_SessionNotFoundErrorが送出される(self) -> None:
        # When / Then
        with pytest.raises(SessionNotFoundError):
            session_store.get_session("non-existent-id")


class TestGetQueue:
    def test_正常系_キューが返される(self) -> None:
        # Given
        session = _make_session()
        created_queue = session_store.create_session(session)

        # When
        result = session_store.get_queue("test-session-id")

        # Then
        assert result is created_queue

    def test_異常系_SessionNotFoundErrorが送出される(self) -> None:
        # When / Then
        with pytest.raises(SessionNotFoundError):
            session_store.get_queue("non-existent-id")


class TestDeleteSession:
    def test_セッションが削除される(self) -> None:
        # Given
        session = _make_session()
        session_store.create_session(session)

        # When
        session_store.delete_session("test-session-id")

        # Then
        assert "test-session-id" not in session_store._sessions
        assert "test-session-id" not in session_store._event_queues

    def test_存在しないセッションの削除はエラーにならない(self) -> None:
        # When / Then (no exception)
        session_store.delete_session("non-existent-id")
