import asyncio

from app.models.debate import DebateEventQueue, DebateSession
from app.models.errors import SessionNotFoundError

_sessions: dict[str, DebateSession] = {}
_event_queues: dict[str, DebateEventQueue] = {}


def create_session(session: DebateSession) -> DebateEventQueue:
    """セッションを保存し、イベントキューを返す。"""
    queue: DebateEventQueue = asyncio.Queue()
    _sessions[session.session_id] = session
    _event_queues[session.session_id] = queue
    return queue


def get_session(session_id: str) -> DebateSession:
    """セッションを取得する。存在しない場合は SessionNotFoundError を送出する。"""
    session = _sessions.get(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    return session


def get_queue(session_id: str) -> DebateEventQueue:
    """イベントキューを取得する。存在しない場合は SessionNotFoundError を送出する。"""
    queue = _event_queues.get(session_id)
    if queue is None:
        raise SessionNotFoundError(session_id)
    return queue


def delete_queue(session_id: str) -> None:
    """SSEストリーム終了後にイベントキューのみを削除する。

    セッション本体（DebateSession）はエクスポート用に保持する。
    """
    _event_queues.pop(session_id, None)


def delete_session(session_id: str) -> None:
    """セッションとキューを両方削除する。"""
    _sessions.pop(session_id, None)
    _event_queues.pop(session_id, None)
