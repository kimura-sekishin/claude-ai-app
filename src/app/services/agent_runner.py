from __future__ import annotations

import os
from typing import Any, cast

import anthropic
from anthropic.types import MessageParam, ToolParam

from app.infra.web_search import WebSearchTool
from app.models.debate import (
    DebateEventQueue,
    DebateTurn,
    Persona,
    Speaker,
    ToolCall,
)
from app.models.errors import LLMError, SearchError

# ツール定義（Claudeに渡す形式）
_WEB_SEARCH_TOOL: ToolParam = cast(
    ToolParam,
    {
        "name": "web_search",
        "description": (
            "インターネットでリアルタイム情報を検索します。"
            "最新のデータや統計、ニュースを根拠として使いたいときに使用してください。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ（日本語または英語）",
                }
            },
            "required": ["query"],
        },
    },
)

_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def _build_system_prompt(persona: Persona, theme: str) -> str:
    return (
        f"あなたは {persona.name} です。\n"
        f"{persona.description}\n\n"
        f"テーマ「{theme}」について議論してください。\n"
        "相手の主張に対して、あなたの立場から論理的に反論・主張してください。\n"
        "根拠が必要な場合はweb_searchツールを使って最新情報を検索してください。\n"
        "発言は200〜400字程度にまとめてください。"
    )


def _build_messages(
    history: list[DebateTurn],
    current_speaker: Speaker,
    theme: str,
) -> list[MessageParam]:
    """会話履歴をAnthropicのmessages形式に変換する。"""
    messages: list[dict[str, Any]] = []

    if not history:
        # 最初の発言: テーマを提示するユーザーメッセージを追加
        messages.append(
            {
                "role": "user",
                "content": f"以下のテーマで議論を始めてください: {theme}",
            }
        )
        return cast(list[MessageParam], messages)

    for turn in history:
        role = "assistant" if turn.speaker == current_speaker else "user"
        messages.append({"role": role, "content": turn.content})

    # 最後が "assistant" の場合は続きを促すユーザーメッセージが必要
    if messages and messages[-1]["role"] == "assistant":
        messages.append(
            {"role": "user", "content": "続けて、あなたの主張を述べてください。"}
        )

    return cast(list[MessageParam], messages)


class AgentRunner:
    """1ペルソナの1ターン発言を生成するエージェント。"""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropicBedrock(
            aws_access_key=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        )
        self._search_tool = WebSearchTool()

    async def run(
        self,
        persona: Persona,
        theme: str,
        history: list[DebateTurn],
        event_queue: DebateEventQueue,
        speaker: Speaker,
    ) -> DebateTurn:
        """1ペルソナの1ターン発言を生成する。

        Args:
            persona: 発言するペルソナ
            theme: 議論テーマ
            history: これまでの発言履歴
            event_queue: SSEイベント送信先キュー
            speaker: このペルソナのスピーカーID ("persona_a" or "persona_b")

        Returns:
            生成されたDebateTurn

        Raises:
            LLMError: Bedrock API呼び出しに失敗した場合
        """
        # turn_start イベント
        await event_queue.put(
            {"type": "turn_start", "speaker": speaker, "name": persona.name}
        )

        system_prompt = _build_system_prompt(persona, theme)
        messages = _build_messages(history, speaker, theme)
        tool_calls_log: list[ToolCall] = []

        try:
            response = await self._client.messages.create(
                model=_MODEL_ID,
                max_tokens=1024,
                system=system_prompt,
                tools=[_WEB_SEARCH_TOOL],
                messages=messages,
            )
        except Exception as e:
            raise LLMError(f"Bedrock API呼び出しに失敗しました: {e}") from e

        # tool_use ループ
        while response.stop_reason == "tool_use":
            # tool_use ブロックを処理
            assistant_content = list(response.content)
            tool_results: list[dict[str, Any]] = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                query = str(block.input.get("query", ""))

                # tool_start イベント
                await event_queue.put(
                    {
                        "type": "tool_start",
                        "speaker": speaker,
                        "tool": "web_search",
                        "query": query,
                    }
                )

                # Web検索実行（失敗しても継続）
                try:
                    search_result = await self._search_tool.search(query)
                    result_summary = "検索結果を取得しました"
                except SearchError:
                    search_result = "検索結果を取得できませんでした。"
                    result_summary = "検索に失敗しました"

                # tool_end イベント
                await event_queue.put(
                    {
                        "type": "tool_end",
                        "speaker": speaker,
                        "tool": "web_search",
                        "result_summary": result_summary,
                    }
                )

                tool_calls_log.append(
                    ToolCall(
                        tool_name="web_search",
                        input={"query": query},
                        output=search_result,
                    )
                )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": search_result,
                    }
                )

            # tool_result を追加して再呼び出し
            extra = cast(
                list[MessageParam],
                [
                    {"role": "assistant", "content": assistant_content},
                    {"role": "user", "content": tool_results},
                ],
            )
            messages = list(messages) + extra

            try:
                response = await self._client.messages.create(
                    model=_MODEL_ID,
                    max_tokens=1024,
                    system=system_prompt,
                    tools=[_WEB_SEARCH_TOOL],
                    messages=messages,
                )
            except Exception as e:
                raise LLMError(f"Bedrock API呼び出しに失敗しました: {e}") from e

        # テキスト内容を抽出
        content_text = ""
        for block in response.content:
            if block.type == "text":
                content_text += block.text

        # token イベント（非ストリーミング版: 全文を1回送信）
        await event_queue.put(
            {"type": "token", "speaker": speaker, "text": content_text}
        )

        # turn_end イベント
        await event_queue.put(
            {"type": "turn_end", "speaker": speaker, "content": content_text}
        )

        return DebateTurn(
            speaker=speaker,
            content=content_text,
            tool_calls=tool_calls_log,
        )
