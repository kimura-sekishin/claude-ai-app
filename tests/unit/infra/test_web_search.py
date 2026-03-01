from unittest.mock import MagicMock

import pytest

from app.infra.web_search import WebSearchTool
from app.models.errors import SearchError


def _make_search_tool(
    search_return: object | None = None,
    search_side_effect: Exception | None = None,
) -> WebSearchTool:
    """モッククライアントを注入したWebSearchToolを返す。"""
    mock_client = MagicMock()
    if search_side_effect is not None:
        mock_client.search.side_effect = search_side_effect
    elif search_return is not None:
        mock_client.search.return_value = search_return
    return WebSearchTool(client=mock_client)


class TestWebSearchTool:
    async def test_正常系_検索結果がテキスト形式で返される(self) -> None:
        # Given
        mock_response = {
            "results": [
                {
                    "title": "AI投資の現状",
                    "content": "2025年のAI投資は過去最高を記録した。",
                },
                {"title": "ROI分析", "content": "平均ROIは30%に達している。"},
            ]
        }
        tool = _make_search_tool(search_return=mock_response)

        # When
        result = await tool.search("AI投資 ROI")

        # Then
        assert "AI投資の現状" in result
        assert "2025年のAI投資は過去最高を記録した" in result
        assert "ROI分析" in result

    async def test_正常系_結果が空の場合はメッセージを返す(self) -> None:
        # Given
        tool = _make_search_tool(search_return={"results": []})

        # When
        result = await tool.search("存在しないクエリ")

        # Then
        assert "見つかりませんでした" in result

    async def test_異常系_API失敗時にSearchErrorが送出される(self) -> None:
        # Given
        tool = _make_search_tool(search_side_effect=RuntimeError("API接続失敗"))

        # When / Then
        with pytest.raises(SearchError, match="Web検索に失敗しました"):
            await tool.search("クエリ")
