import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.debate import (
    DebateConfig,
    DebateEventQueue,
    DebateSession,
    DebateStatus,
    DebateTurn,
    Persona,
)
from app.models.errors import LLMError
from app.services.debate_orchestrator import DebateOrchestrator


def _make_config(max_turns: int = 1) -> DebateConfig:
    return DebateConfig(
        persona_a=Persona(name="楽観コンサル", description="AI投資に積極的"),
        persona_b=Persona(name="慎重アナリスト", description="リスク重視"),
        theme="AIへの投資はすべきか",
        max_turns=max_turns,
    )


def _make_session(config: DebateConfig) -> DebateSession:
    return DebateSession(
        session_id="test-session",
        config=config,
        status=DebateStatus.RUNNING,
    )


def _make_turn(speaker: str, content: str) -> DebateTurn:
    turn = MagicMock(spec=DebateTurn)
    turn.speaker = speaker
    turn.content = content
    return turn


def _make_summary_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@pytest.fixture
def orchestrator(monkeypatch: pytest.MonkeyPatch) -> DebateOrchestrator:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")

    with (
        patch("app.services.debate_orchestrator.AgentRunner"),
        patch("app.services.debate_orchestrator.anthropic.AsyncAnthropicBedrock"),
    ):
        orch = DebateOrchestrator()

    return orch


@pytest.fixture
def event_queue() -> DebateEventQueue:
    return asyncio.Queue()


class TestDebateOrchestratorNormal:
    async def test_全ターン完了後にcompleteイベントが送信される(
        self,
        orchestrator: DebateOrchestrator,
        event_queue: DebateEventQueue,
    ) -> None:
        # Given
        config = _make_config(max_turns=1)
        session = _make_session(config)

        orchestrator._agent_runner.run = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[
                _make_turn("persona_a", "AIへの投資は今がチャンスです。"),
                _make_turn("persona_b", "リスクを考慮すべきです。"),
            ]
        )
        orchestrator._bedrock_client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            return_value=_make_summary_response("両者の主張をまとめると…")
        )

        # When
        await orchestrator.run(config=config, event_queue=event_queue, session=session)

        # Then: complete イベントが最後に届く
        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())

        event_types = [e["type"] for e in events]
        assert "complete" in event_types
        assert event_types[-1] == "complete"
        assert events[-1]["session_id"] == "test-session"

    async def test_全発言がsession_turnsに記録される(
        self,
        orchestrator: DebateOrchestrator,
        event_queue: DebateEventQueue,
    ) -> None:
        # Given
        config = _make_config(max_turns=2)
        session = _make_session(config)

        orchestrator._agent_runner.run = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[
                _make_turn("persona_a", "発言A1"),
                _make_turn("persona_b", "発言B1"),
                _make_turn("persona_a", "発言A2"),
                _make_turn("persona_b", "発言B2"),
            ]
        )
        orchestrator._bedrock_client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            return_value=_make_summary_response("まとめ")
        )

        # When
        await orchestrator.run(config=config, event_queue=event_queue, session=session)

        # Then: 4ターン（2ラウンド × 2人）が記録される
        assert len(session.turns) == 4

    async def test_session_summaryにまとめが設定される(
        self,
        orchestrator: DebateOrchestrator,
        event_queue: DebateEventQueue,
    ) -> None:
        # Given
        config = _make_config(max_turns=1)
        session = _make_session(config)

        orchestrator._agent_runner.run = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[
                _make_turn("persona_a", "発言A"),
                _make_turn("persona_b", "発言B"),
            ]
        )
        orchestrator._bedrock_client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            return_value=_make_summary_response("生成されたまとめテキスト")
        )

        # When
        await orchestrator.run(config=config, event_queue=event_queue, session=session)

        # Then
        assert session.summary == "生成されたまとめテキスト"

    async def test_session_statusがCOMPLETEDになる(
        self,
        orchestrator: DebateOrchestrator,
        event_queue: DebateEventQueue,
    ) -> None:
        # Given
        config = _make_config(max_turns=1)
        session = _make_session(config)

        orchestrator._agent_runner.run = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[
                _make_turn("persona_a", "発言A"),
                _make_turn("persona_b", "発言B"),
            ]
        )
        orchestrator._bedrock_client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            return_value=_make_summary_response("まとめ")
        )

        # When
        await orchestrator.run(config=config, event_queue=event_queue, session=session)

        # Then
        assert session.status == DebateStatus.COMPLETED


class TestDebateOrchestratorError:
    async def test_LLMError発生時にerrorイベントが送信される(
        self,
        orchestrator: DebateOrchestrator,
        event_queue: DebateEventQueue,
    ) -> None:
        # Given: AgentRunnerがLLMErrorを送出するモック
        config = _make_config(max_turns=1)
        session = _make_session(config)

        orchestrator._agent_runner.run = AsyncMock(  # type: ignore[attr-defined]
            side_effect=LLMError("Bedrock接続エラー")
        )

        # When
        await orchestrator.run(config=config, event_queue=event_queue, session=session)

        # Then: error イベントが送信される
        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())

        assert any(e["type"] == "error" for e in events)

    async def test_LLMError発生時にsession_statusがERRORになる(
        self,
        orchestrator: DebateOrchestrator,
        event_queue: DebateEventQueue,
    ) -> None:
        # Given
        config = _make_config(max_turns=1)
        session = _make_session(config)

        orchestrator._agent_runner.run = AsyncMock(  # type: ignore[attr-defined]
            side_effect=LLMError("API失敗")
        )

        # When
        await orchestrator.run(config=config, event_queue=event_queue, session=session)

        # Then
        assert session.status == DebateStatus.ERROR

    async def test_まとめ生成失敗時にerrorイベントが送信される(
        self,
        orchestrator: DebateOrchestrator,
        event_queue: DebateEventQueue,
    ) -> None:
        # Given: AgentRunnerは成功するがまとめ生成で失敗するモック
        config = _make_config(max_turns=1)
        session = _make_session(config)

        orchestrator._agent_runner.run = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[
                _make_turn("persona_a", "発言A"),
                _make_turn("persona_b", "発言B"),
            ]
        )
        orchestrator._bedrock_client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            side_effect=Exception("Bedrock接続タイムアウト")
        )

        # When
        await orchestrator.run(config=config, event_queue=event_queue, session=session)

        # Then: error イベントが送信される
        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())

        assert any(e["type"] == "error" for e in events)
        assert session.status == DebateStatus.ERROR
