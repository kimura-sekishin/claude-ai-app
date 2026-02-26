import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.debate import DebateEventQueue, DebateTurn, Persona
from app.models.errors import LLMError, SearchError
from app.services.agent_runner import MAX_SEARCHES_PER_TURN, AgentRunner


def _make_text_block(text: str) -> MagicMock:
    """TextBlock のモックを作成する。"""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(tool_id: str, query: str) -> MagicMock:
    """ToolUseBlock のモックを作成する。"""
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = "web_search"
    block.input = {"query": query}
    return block


def _make_response(stop_reason: str, content: list[Any]) -> MagicMock:
    """Bedrock messages.create() のレスポンスモックを作成する。"""
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content
    return response


@pytest.fixture
def agent_runner(monkeypatch: pytest.MonkeyPatch) -> AgentRunner:
    """環境変数をセットし、外部クライアントをモックしたAgentRunnerを返す。"""
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")

    with (
        patch("app.services.agent_runner.anthropic.AsyncAnthropicBedrock"),
        patch("app.services.agent_runner.WebSearchTool"),
    ):
        runner = AgentRunner()

    return runner


@pytest.fixture
def event_queue() -> DebateEventQueue:
    return asyncio.Queue()


@pytest.fixture
def persona_a() -> Persona:
    return Persona(name="楽観コンサル", description="AI投資に積極的な立場")


class TestAgentRunnerNoTool:
    async def test_ツールなしの発言_正しいイベント順序で送信される(
        self,
        agent_runner: AgentRunner,
        event_queue: DebateEventQueue,
        persona_a: Persona,
    ) -> None:
        # Given: ツールを使わずにテキストを返すモックレスポンス
        text_response = _make_response(
            stop_reason="end_turn",
            content=[_make_text_block("AIへの投資は今が最大のチャンスです。")],
        )
        agent_runner._client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            return_value=text_response
        )

        # When
        result = await agent_runner.run(
            persona=persona_a,
            theme="AIベンチャーへの投資はすべきか",
            history=[],
            event_queue=event_queue,
            speaker="persona_a",
        )

        # Then: DebateTurn が返される
        assert isinstance(result, DebateTurn)
        assert result.speaker == "persona_a"
        assert result.content == "AIへの投資は今が最大のチャンスです。"
        assert result.tool_calls == []

        # Then: イベント順序を確認 (turn_start → token → turn_end)
        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())

        assert len(events) == 3
        assert events[0]["type"] == "turn_start"
        assert events[0]["speaker"] == "persona_a"
        assert events[0]["name"] == "楽観コンサル"

        assert events[1]["type"] == "token"
        assert events[1]["text"] == "AIへの投資は今が最大のチャンスです。"

        assert events[2]["type"] == "turn_end"
        assert events[2]["content"] == "AIへの投資は今が最大のチャンスです。"


class TestAgentRunnerWithTool:
    async def test_ツールあり_tool_startとtool_endイベントが送信される(
        self,
        agent_runner: AgentRunner,
        event_queue: DebateEventQueue,
        persona_a: Persona,
    ) -> None:
        # Given: 1回tool_useを返し、その後テキストを返すモック
        tool_response = _make_response(
            stop_reason="tool_use",
            content=[_make_tool_use_block("tool-001", "AI投資 ROI 2025")],
        )
        text_response = _make_response(
            stop_reason="end_turn",
            content=[
                _make_text_block("Gartnerの調査によると、AIへの投資ROIは30%です。")
            ],
        )
        agent_runner._client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[tool_response, text_response]
        )
        agent_runner._search_tool.search = AsyncMock(  # type: ignore[attr-defined]
            return_value="AI投資のROIは30%に達している（Gartner 2025）"
        )

        # When
        result = await agent_runner.run(
            persona=persona_a,
            theme="AIベンチャーへの投資はすべきか",
            history=[],
            event_queue=event_queue,
            speaker="persona_a",
        )

        # Then: DebateTurn にToolCallが記録される
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "web_search"
        assert result.tool_calls[0].input == {"query": "AI投資 ROI 2025"}

        # Then: イベント順序 (turn_start→tool_start→tool_end→token→turn_end)
        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())

        event_types = [e["type"] for e in events]
        assert event_types == [
            "turn_start",
            "tool_start",
            "tool_end",
            "token",
            "turn_end",
        ]

        assert events[1]["tool"] == "web_search"
        assert events[1]["query"] == "AI投資 ROI 2025"
        assert events[2]["tool"] == "web_search"


class TestAgentRunnerSearchError:
    async def test_検索失敗でも議論が継続される(
        self,
        agent_runner: AgentRunner,
        event_queue: DebateEventQueue,
        persona_a: Persona,
    ) -> None:
        # Given: tool_use後にSearchErrorが発生するモック
        tool_response = _make_response(
            stop_reason="tool_use",
            content=[_make_tool_use_block("tool-002", "失敗クエリ")],
        )
        text_response = _make_response(
            stop_reason="end_turn",
            content=[_make_text_block("検索なしでも議論を続けます。")],
        )
        agent_runner._client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[tool_response, text_response]
        )
        agent_runner._search_tool.search = AsyncMock(  # type: ignore[attr-defined]
            side_effect=SearchError("検索失敗")
        )

        # When: 例外が発生しないことを確認
        result = await agent_runner.run(
            persona=persona_a,
            theme="テーマ",
            history=[],
            event_queue=event_queue,
            speaker="persona_a",
        )

        # Then: 議論が継続して DebateTurn が返される
        assert result.content == "検索なしでも議論を続けます。"

        # Then: tool_end イベントに失敗メッセージが含まれる
        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())

        tool_end_event = next(e for e in events if e["type"] == "tool_end")
        assert "失敗" in str(tool_end_event["result_summary"])


class TestAgentRunnerLLMError:
    async def test_Bedrock呼び出し失敗時にLLMErrorが送出される(
        self,
        agent_runner: AgentRunner,
        event_queue: DebateEventQueue,
        persona_a: Persona,
    ) -> None:
        # Given: Bedrock APIが例外を送出するモック
        agent_runner._client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            side_effect=RuntimeError("Bedrock接続エラー")
        )

        # When / Then: LLMError が送出される
        with pytest.raises(LLMError, match="Bedrock API呼び出しに失敗しました"):
            await agent_runner.run(
                persona=persona_a,
                theme="テーマ",
                history=[],
                event_queue=event_queue,
                speaker="persona_a",
            )


class TestAgentRunnerSearchLimit:
    async def test_検索上限到達後はtools空リストで呼び出される(
        self,
        agent_runner: AgentRunner,
        event_queue: DebateEventQueue,
        persona_a: Persona,
    ) -> None:
        # Given: MAX_SEARCHES_PER_TURN回のtool_useの後にテキストを返すモック
        tool_responses = [
            _make_response(
                stop_reason="tool_use",
                content=[_make_tool_use_block(f"tool-{i:03}", f"クエリ{i}")],
            )
            for i in range(MAX_SEARCHES_PER_TURN)
        ]
        text_response = _make_response(
            stop_reason="end_turn",
            content=[_make_text_block("上限到達後の発言")],
        )
        agent_runner._client.messages.create = AsyncMock(  # type: ignore[attr-defined]
            side_effect=[*tool_responses, text_response]
        )
        agent_runner._search_tool.search = AsyncMock(  # type: ignore[attr-defined]
            return_value="検索結果"
        )

        # When
        result = await agent_runner.run(
            persona=persona_a,
            theme="テーマ",
            history=[],
            event_queue=event_queue,
            speaker="persona_a",
        )

        # Then: 合計 MAX_SEARCHES_PER_TURN + 1 回のAPIコール
        mock_create = agent_runner._client.messages.create  # type: ignore[attr-defined]
        assert mock_create.call_count == MAX_SEARCHES_PER_TURN + 1

        # Then: 最後のAPIコール（上限到達後）は tools=[] で呼ばれる
        last_call_kwargs = mock_create.call_args_list[-1].kwargs
        assert last_call_kwargs["tools"] == []

        # Then: DebateTurn に MAX_SEARCHES_PER_TURN 分のツール呼び出しが記録される
        assert len(result.tool_calls) == MAX_SEARCHES_PER_TURN
        assert result.content == "上限到達後の発言"
