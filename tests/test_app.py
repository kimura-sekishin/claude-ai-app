import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestAppStartup:
    async def test_アプリが起動しAPIルーターが登録されている(
        self, client: AsyncClient
    ) -> None:
        # When: 存在しないIDでdebate開始エンドポイントにアクセス
        response = await client.post(
            "/api/debate/start",
            json={
                "persona_a": {"name": "A", "description": "Aの立場"},
                "persona_b": {"name": "B", "description": "Bの立場"},
                "theme": "テスト議論テーマ",
            },
        )

        # Then: 200 (アプリが正常に起動し、ルーターが登録されている)
        assert response.status_code == 200
        assert "session_id" in response.json()
