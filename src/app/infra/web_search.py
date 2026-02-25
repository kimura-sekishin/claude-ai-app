from __future__ import annotations

import asyncio
import os

from tavily import TavilyClient

from app.models.errors import SearchError


class WebSearchTool:
    """Tavily APIを使ったWeb検索ツール。"""

    def __init__(self) -> None:
        api_key = os.environ["TAVILY_API_KEY"]
        self._client = TavilyClient(api_key=api_key)

    async def search(self, query: str) -> str:
        """Web検索を実行し、結果をテキスト形式で返す。

        Args:
            query: 検索クエリ

        Returns:
            上位3件の検索結果（タイトル + コンテンツ）を連結したテキスト

        Raises:
            SearchError: Tavily API呼び出しに失敗した場合
        """
        try:
            response: dict[str, object] = await asyncio.to_thread(
                self._client.search,
                query,
                max_results=3,
            )
        except Exception as e:
            raise SearchError(f"Web検索に失敗しました: {e}") from e

        results = response.get("results", [])
        if not isinstance(results, list) or not results:
            return "検索結果が見つかりませんでした。"

        parts: list[str] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = item.get("title", "")
            content = item.get("content", "")
            if title or content:
                parts.append(f"【{title}】\n{content}")

        return "\n\n".join(parts) if parts else "検索結果が見つかりませんでした。"
