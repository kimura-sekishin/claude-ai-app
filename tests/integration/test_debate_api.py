import pytest
from httpx import ASGITransport, AsyncClient

from app.infra import session_store
from app.main import app
from app.models.debate import DEFAULT_PERSONA_A, DEFAULT_PERSONA_B

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

    async def test_正常系_テーマのみで開始できる(self, client: AsyncClient) -> None:
        # Given: ペルソナ省略、テーマのみ
        request = {"theme": "AIベンチャーへの投資はすべきか"}

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then: デフォルトペルソナで200が返る
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        assert session_id
        # デフォルトペルソナが適用されていることを値レベルで確認
        session = session_store.get_session(session_id)
        assert session.config.persona_a.name == DEFAULT_PERSONA_A.name
        assert session.config.persona_b.name == DEFAULT_PERSONA_B.name

    async def test_正常系_名前のみ指定で200が返る(self, client: AsyncClient) -> None:
        # Given: 名前のみ指定（説明は省略）
        request = {
            "persona_a": {"name": "AI推進派"},
            "persona_b": {"name": "AI懐疑派"},
            "theme": "AIは社会を豊かにするか",
        }

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then
        assert response.status_code == 200

    async def test_正常系_空白入力でデフォルト適用(self, client: AsyncClient) -> None:
        # Given: 空白のみ（strip後に空になる）
        request = {
            **VALID_REQUEST,
            "persona_a": {"name": "   ", "description": "   "},
        }

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then: デフォルトにフォールバックして200
        assert response.status_code == 200

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


class TestExportDebate:
    async def test_正常系_Markdownファイルが返される(self, client: AsyncClient) -> None:
        # Given: 有効なセッションを作成
        start_response = await client.post("/api/debate/start", json=VALID_REQUEST)
        session_id = start_response.json()["session_id"]

        # When
        response = await client.get(f"/api/debate/{session_id}/export")

        # Then
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        content = response.text
        assert "# 議論:" in content
        assert "## ペルソナ設定" in content

    async def test_正常系_Markdownにテーマが含まれる(self, client: AsyncClient) -> None:
        # Given
        request = {**VALID_REQUEST, "theme": "AIは人類を幸福にするか"}
        start_response = await client.post("/api/debate/start", json=request)
        session_id = start_response.json()["session_id"]

        # When
        response = await client.get(f"/api/debate/{session_id}/export")

        # Then
        assert "AIは人類を幸福にするか" in response.text

    async def test_異常系_存在しないsession_idで404(self, client: AsyncClient) -> None:
        # When
        response = await client.get("/api/debate/non-existent-id/export")

        # Then
        assert response.status_code == 404


class TestMaxTurns:
    async def test_正常系_max_turns_1で200が返る(self, client: AsyncClient) -> None:
        # Given
        request = {**VALID_REQUEST, "max_turns": 1}

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        session = session_store.get_session(session_id)
        assert session.config.max_turns == 1

    async def test_正常系_max_turns_6で200が返る(self, client: AsyncClient) -> None:
        # Given
        request = {**VALID_REQUEST, "max_turns": 6}

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        session = session_store.get_session(session_id)
        assert session.config.max_turns == 6

    async def test_正常系_max_turns省略でデフォルト2が適用される(
        self, client: AsyncClient
    ) -> None:
        # Given: max_turns を指定しない
        request = {"theme": "AIは社会を豊かにするか"}

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        session = session_store.get_session(session_id)
        assert session.config.max_turns == 2

    async def test_異常系_max_turns_0で422(self, client: AsyncClient) -> None:
        # Given
        request = {**VALID_REQUEST, "max_turns": 0}

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then
        assert response.status_code == 422

    async def test_異常系_max_turns_7で422(self, client: AsyncClient) -> None:
        # Given
        request = {**VALID_REQUEST, "max_turns": 7}

        # When
        response = await client.post("/api/debate/start", json=request)

        # Then
        assert response.status_code == 422
