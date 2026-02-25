from unittest.mock import MagicMock, patch

import pytest

from app.infra.web_search import WebSearchTool
from app.models.errors import SearchError


class TestWebSearchTool:
    async def test_正常系_検索結果がテキスト形式で返される(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Given
        monkeypatch.setenv("TAVILY_API_KEY", "test-api-key")
        mock_response = {
            "results": [
                {
                    "title": "AI投資の現状",
                    "content": "2025年のAI投資は過去最高を記録した。",
                },
                {"title": "ROI分析", "content": "平均ROIは30%に達している。"},
            ]
        }

        with patch("app.infra.web_search.TavilyClient") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.search.return_value = mock_response
            mock_client_cls.return_value = mock_instance

            tool = WebSearchTool()

        # When
        result = await tool.search("AI投資 ROI")

        # Then
        assert "AI投資の現状" in result
        assert "2025年のAI投資は過去最高を記録した" in result
        assert "ROI分析" in result

    async def test_正常系_結果が空の場合はメッセージを返す(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Given
        monkeypatch.setenv("TAVILY_API_KEY", "test-api-key")
        mock_response: dict[str, object] = {"results": []}

        with patch("app.infra.web_search.TavilyClient") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.search.return_value = mock_response
            mock_client_cls.return_value = mock_instance

            tool = WebSearchTool()

        # When
        result = await tool.search("存在しないクエリ")

        # Then
        assert "見つかりませんでした" in result

    async def test_異常系_API失敗時にSearchErrorが送出される(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Given
        monkeypatch.setenv("TAVILY_API_KEY", "test-api-key")

        with patch("app.infra.web_search.TavilyClient") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.search.side_effect = RuntimeError("API接続失敗")
            mock_client_cls.return_value = mock_instance

            tool = WebSearchTool()

        # When / Then
        with pytest.raises(SearchError, match="Web検索に失敗しました"):
            await tool.search("クエリ")
