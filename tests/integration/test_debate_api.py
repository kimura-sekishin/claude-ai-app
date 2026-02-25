import pytest
from httpx import ASGITransport, AsyncClient

from app.infra import session_store
from app.main import app

BASE_URL = "http://testserver"

VALID_REQUEST = {
    "persona_a": {
        "name": "楽観的なコンサルタント",
        "description": "AI投資に積極的。成長機会を重視して主張する。",
    },
    "persona_b": {
        "name": "慎重なリスクアナリスト",
        "description": "リスク管理を重視。データに基づいて反論する。",
    },
    "theme": "AIベンチャーへの投資はすべきか",
}


@pytest.fixture(autouse=True)
def cleanup_store() -> object:
    """各テスト後にストアをクリアする。"""
    yield
    session_store._sessions.clear()
    session_store._event_queues.clear()


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as ac:
        yield ac


class TestStartDebate:
    async def test_正常系_session_idが返される(self, client: AsyncClient) -> None:
        # When
        response = await client.post("/api/debate/start", json=VALID_REQUEST)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) == 36  # UUID形式

    async def test_異常系_persona_a_name空文字で422(self, client: AsyncClient) -> None:
        # Given
        invalid_request = {
            **VALID_REQUEST,
            "persona_a": {"name": "", "description": "説明"},
        }

        # When
        response = await client.post("/api/debate/start", json=invalid_request)

        # Then
        assert response.status_code == 422

    async def test_異常系_theme空文字で422(self, client: AsyncClient) -> None:
        # Given
        invalid_request = {**VALID_REQUEST, "theme": ""}

        # When
        response = await client.post("/api/debate/start", json=invalid_request)

        # Then
        assert response.status_code == 422

    async def test_異常系_フィールド欠損で422(self, client: AsyncClient) -> None:
        # Given
        invalid_request = {"persona_a": VALID_REQUEST["persona_a"]}

        # When
        response = await client.post("/api/debate/start", json=invalid_request)

        # Then
        assert response.status_code == 422


class TestStreamDebate:
    async def test_異常系_存在しないsession_idで404(self, client: AsyncClient) -> None:
        # When
        response = await client.get("/api/debate/non-existent-session-id/stream")

        # Then
        assert response.status_code == 404
