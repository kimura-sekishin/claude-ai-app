from app.models.debate import DebateSession


def format_debate_as_markdown(session: DebateSession) -> str:
    """議論セッションをMarkdown形式に変換する。

    将来のDB履歴機能でも再利用できるよう、独立した関数として実装する。

    Args:
        session: 変換対象の議論セッション

    Returns:
        Markdown形式の文字列
    """
    config = session.config
    lines: list[str] = []

    # タイトル
    lines.append(f"# 議論: {config.theme}")
    lines.append("")

    # ペルソナ設定
    lines.append("## ペルソナ設定")
    lines.append("")
    lines.append(f"### ペルソナ A: {config.persona_a.name}")
    lines.append(config.persona_a.description)
    lines.append("")
    lines.append(f"### ペルソナ B: {config.persona_b.name}")
    lines.append(config.persona_b.description)
    lines.append("")

    # 議論の内容
    if session.turns:
        lines.append("---")
        lines.append("")
        lines.append("## 議論の内容")
        lines.append("")

        for turn in session.turns:
            speaker_persona = (
                config.persona_a if turn.speaker == "persona_a" else config.persona_b
            )
            lines.append(f"### {speaker_persona.name}")
            lines.append("")
            lines.append(turn.content)
            lines.append("")

    # まとめ
    if session.summary:
        lines.append("---")
        lines.append("")
        lines.append("## まとめ")
        lines.append("")
        lines.append(session.summary)
        lines.append("")

    return "\n".join(lines)
