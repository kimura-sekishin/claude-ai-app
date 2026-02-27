from app.models.debate import (
    DebateConfig,
    DebateSession,
    DebateStatus,
    DebateTurn,
    Persona,
)
from app.services.debate_formatter import format_debate_as_markdown


def _make_session(
    theme: str = "AIへの投資はすべきか",
    persona_a_name: str = "賛成派",
    persona_a_desc: str = "AIに積極的な立場",
    persona_b_name: str = "反対派",
    persona_b_desc: str = "リスクを重視する立場",
    turns: list[DebateTurn] | None = None,
    summary: str | None = None,
    status: DebateStatus = DebateStatus.COMPLETED,
) -> DebateSession:
    config = DebateConfig(
        persona_a=Persona(name=persona_a_name, description=persona_a_desc),
        persona_b=Persona(name=persona_b_name, description=persona_b_desc),
        theme=theme,
    )
    return DebateSession(
        session_id="test-session-id",
        config=config,
        turns=turns or [],
        summary=summary,
        status=status,
    )


class TestFormatDebateAsMarkdown:
    def test_タイトルにテーマが含まれる(self) -> None:
        # Given
        session = _make_session(theme="AIベンチャーへの投資はすべきか")

        # When
        result = format_debate_as_markdown(session)

        # Then
        assert "# 議論: AIベンチャーへの投資はすべきか" in result

    def test_ペルソナ情報が含まれる(self) -> None:
        # Given
        session = _make_session(
            persona_a_name="楽観コンサル",
            persona_a_desc="AI投資に積極的",
            persona_b_name="慎重アナリスト",
            persona_b_desc="リスク重視",
        )

        # When
        result = format_debate_as_markdown(session)

        # Then
        assert "### ペルソナ A: 楽観コンサル" in result
        assert "AI投資に積極的" in result
        assert "### ペルソナ B: 慎重アナリスト" in result
        assert "リスク重視" in result

    def test_発言ターンが含まれる(self) -> None:
        # Given
        turns = [
            DebateTurn(
                speaker="persona_a",
                content="AIへの投資は今が最大のチャンスです。",
            ),
            DebateTurn(speaker="persona_b", content="リスク管理が重要です。"),
        ]
        session = _make_session(turns=turns)

        # When
        result = format_debate_as_markdown(session)

        # Then
        assert "AIへの投資は今が最大のチャンスです。" in result
        assert "リスク管理が重要です。" in result

    def test_発言者名がspeaker名でなくペルソナ名になる(self) -> None:
        # Given: persona_aの名前は「賛成派」
        turns = [
            DebateTurn(speaker="persona_a", content="賛成します。"),
        ]
        session = _make_session(persona_a_name="賛成派", turns=turns)

        # When
        result = format_debate_as_markdown(session)

        # Then: "persona_a"ではなく"賛成派"で表示される
        assert "### 賛成派" in result
        assert "persona_a" not in result

    def test_まとめが含まれる(self) -> None:
        # Given
        session = _make_session(summary="両者の意見をまとめると...")

        # When
        result = format_debate_as_markdown(session)

        # Then
        assert "## まとめ" in result
        assert "両者の意見をまとめると..." in result

    def test_まとめなしの場合はまとめセクションが含まれない(self) -> None:
        # Given
        session = _make_session(summary=None)

        # When
        result = format_debate_as_markdown(session)

        # Then
        assert "## まとめ" not in result

    def test_ターンなしでも正常に動作する(self) -> None:
        # Given
        session = _make_session(turns=[])

        # When
        result = format_debate_as_markdown(session)

        # Then: エラーにならず、ペルソナ情報は含まれる
        assert isinstance(result, str)
        assert "## ペルソナ設定" in result
        assert "## 議論の内容" not in result

    def test_複数ターンが順番通りに含まれる(self) -> None:
        # Given
        turns = [
            DebateTurn(speaker="persona_a", content="ターン1の発言"),
            DebateTurn(speaker="persona_b", content="ターン2の発言"),
            DebateTurn(speaker="persona_a", content="ターン3の発言"),
            DebateTurn(speaker="persona_b", content="ターン4の発言"),
        ]
        session = _make_session(turns=turns)

        # When
        result = format_debate_as_markdown(session)

        # Then: 全ターンが含まれ、順序が保たれる
        idx1 = result.index("ターン1の発言")
        idx2 = result.index("ターン2の発言")
        idx3 = result.index("ターン3の発言")
        idx4 = result.index("ターン4の発言")
        assert idx1 < idx2 < idx3 < idx4

    def test_戻り値はstr型(self) -> None:
        # Given
        session = _make_session()

        # When
        result = format_debate_as_markdown(session)

        # Then
        assert isinstance(result, str)
