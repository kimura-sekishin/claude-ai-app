from __future__ import annotations

import os

import anthropic

from app.models.debate import (
    DebateConfig,
    DebateEventQueue,
    DebateSession,
    DebateStatus,
    Persona,
    Speaker,
)
from app.models.errors import LLMError
from app.services.agent_runner import AgentRunner

_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def _build_summary_prompt(config: DebateConfig, session: DebateSession) -> str:
    """討論まとめ生成のプロンプトを構築する。"""
    a_turns = [t for t in session.turns if t.speaker == "persona_a"]
    b_turns = [t for t in session.turns if t.speaker == "persona_b"]

    a_content = "\n".join(f"- {t.content}" for t in a_turns) or "（発言なし）"
    b_content = "\n".join(f"- {t.content}" for t in b_turns) or "（発言なし）"

    return (
        f"以下のAI討論のまとめを作成してください。\n\n"
        f"テーマ: {config.theme}\n\n"
        f"【{config.persona_a.name}の主な主張】\n{a_content}\n\n"
        f"【{config.persona_b.name}の主な主張】\n{b_content}\n\n"
        "上記を踏まえて、両者の主要な論点と総合的な結論をまとめてください（300字程度）。"
    )


class DebateOrchestrator:
    """議論全体の進行を管理するオーケストレーター。"""

    def __init__(
        self,
        agent_runner: AgentRunner | None = None,
        bedrock_client: anthropic.AsyncAnthropicBedrock | None = None,
    ) -> None:
        self._bedrock_client = bedrock_client or anthropic.AsyncAnthropicBedrock(
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        )
        self._agent_runner = agent_runner or AgentRunner(
            bedrock_client=self._bedrock_client
        )

    async def run(
        self,
        config: DebateConfig,
        event_queue: DebateEventQueue,
        session: DebateSession,
    ) -> None:
        """議論を実行し、セッションをインプレースで更新する。

        Args:
            config: 議論設定（ペルソナ・テーマ・ターン数）
            event_queue: SSEイベント送信先キュー
            session: 更新対象セッション（statusとturnsとsummaryをインプレースで更新）
        """
        try:
            await self._run_debate(config, event_queue, session)
        except LLMError as e:
            session.status = DebateStatus.ERROR
            await event_queue.put({"type": "error", "message": str(e)})
        except Exception:
            session.status = DebateStatus.ERROR
            await event_queue.put(
                {"type": "error", "message": "予期せぬエラーが発生しました"}
            )

    async def _run_debate(
        self,
        config: DebateConfig,
        event_queue: DebateEventQueue,
        session: DebateSession,
    ) -> None:
        """議論ループ → まとめ生成 → complete イベント送信。"""
        # 型安全なターン順序定義
        turn_order: list[tuple[Persona, Speaker]] = [
            (config.persona_a, "persona_a"),
            (config.persona_b, "persona_b"),
        ]

        # 議論ループ（max_turns ラウンド × 2人）
        for _ in range(config.max_turns):
            for persona, speaker in turn_order:
                turn = await self._agent_runner.run(
                    persona=persona,
                    theme=config.theme,
                    history=list(session.turns),
                    event_queue=event_queue,
                    speaker=speaker,
                )
                session.turns.append(turn)

        # まとめ生成（非ストリーミング: summary_token を1回送信）
        await event_queue.put({"type": "summary_start"})

        summary_text = await self._generate_summary(config, session)
        session.summary = summary_text

        await event_queue.put({"type": "summary_token", "text": summary_text})

        # 完了
        session.status = DebateStatus.COMPLETED
        await event_queue.put({"type": "complete", "session_id": session.session_id})

    async def _generate_summary(
        self, config: DebateConfig, session: DebateSession
    ) -> str:
        """全ターンを要約するまとめを生成する（ツールなし）。"""
        prompt = _build_summary_prompt(config, session)

        try:
            response = await self._bedrock_client.messages.create(
                model=_MODEL_ID,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise LLMError(f"まとめの生成に失敗しました: {e}") from e

        summary = ""
        for block in response.content:
            if block.type == "text":
                summary += block.text

        return summary
