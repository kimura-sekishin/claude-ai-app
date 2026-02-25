class DebateError(Exception):
    """議論アプリ基底例外"""


class ValidationError(DebateError):
    """入力バリデーションエラー"""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


class LLMError(DebateError):
    """LLM API呼び出し失敗（議論を中断する）"""


class SearchError(DebateError):
    """Web検索失敗（議論は継続可能）"""


class SessionNotFoundError(DebateError):
    """セッションが見つからない"""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"セッションが見つかりません: {session_id}")
        self.session_id = session_id
