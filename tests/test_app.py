import pytest
from httpx import ASGITransport, AsyncClient

from src.app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestRootEndpoint:
    async def test_returns_hello_world(self, client: AsyncClient) -> None:
        # Given: 起動中のAPIサーバー

        # When: ルートエンドポイントにGETリクエストを送る
        response = await client.get("/")

        # Then: 200とHello Worldメッセージが返る
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}


class TestHealthEndpoint:
    async def test_returns_ok(self, client: AsyncClient) -> None:
        # Given: 起動中のAPIサーバー

        # When: /healthにGETリクエストを送る
        response = await client.get("/health")

        # Then: 200とstatus okが返る
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestItemEndpoint:
    async def test_returns_item_with_id(self, client: AsyncClient) -> None:
        # Given: アイテムID 42

        # When: /items/42にGETリクエストを送る
        response = await client.get("/items/42")

        # Then: 200とアイテム情報が返る
        assert response.status_code == 200
        assert response.json() == {"item_id": 42, "name": None}

    async def test_returns_item_with_name(self, client: AsyncClient) -> None:
        # Given: アイテムID 1 と name クエリパラメータ

        # When: /items/1?name=testにGETリクエストを送る
        response = await client.get("/items/1?name=test")

        # Then: 200とname付きのアイテム情報が返る
        assert response.status_code == 200
        assert response.json() == {"item_id": 1, "name": "test"}
