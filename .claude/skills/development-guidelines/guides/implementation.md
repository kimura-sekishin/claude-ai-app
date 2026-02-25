# 実装ガイド (Implementation Guide)

## Python 規約

### 型定義

**組み込み型の使用**:
```python
# ✅ 良い例: Python 3.10+ の組み込み型を使用
def process_items(items: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        result[item] = result.get(item, 0) + 1
    return result

# ❌ 悪い例: 古いtyping モジュール
from typing import List, Dict
def process_items(items: List[str]) -> Dict[str, int]: ...
```

**型注釈の原則**:
```python
# ✅ 良い例: 明示的な型注釈
def calculate_total(prices: list[float]) -> float:
    return sum(prices)

# ❌ 悪い例: 型注釈なし (mypyでエラー)
def calculate_total(prices):  # Any型になる
    return sum(prices)
```

**TypedDict と dataclass**:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, TypedDict

# TypedDict: 辞書型のスキーマ定義
class TaskDict(TypedDict):
    id: str
    title: str
    completed: bool

# dataclass: 値オブジェクト・エンティティ
TaskStatus = Literal["todo", "in_progress", "completed"]

@dataclass
class Task:
    id: str
    title: str
    status: TaskStatus
    description: str | None = None
```

### 命名規則

**変数・関数**:
```python
# 変数: snake_case、名詞
user_name = "John"
task_list: list[Task] = []
is_completed = True

# 関数: snake_case、動詞で始める
def fetch_user_data() -> User: ...
def validate_email(email: str) -> None: ...
def calculate_total_price(items: list[Item]) -> int: ...

# Boolean: is_, has_, should_, can_ で始める
is_valid = True
has_permission = False
should_retry = True
can_delete = False
```

**クラス**:
```python
# クラス: PascalCase、名詞
class TaskManager: ...
class UserAuthenticationService: ...

# Protocol: インターフェース相当
from typing import Protocol

class TaskRepository(Protocol):
    async def save(self, task: Task) -> None: ...
    async def find_by_id(self, id: str) -> Task | None: ...
```

**定数**:
```python
# UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
API_BASE_URL = "https://api.example.com"
DEFAULT_TIMEOUT = 5000
```

**ファイル名**:
```
# すべて snake_case
# task_service.py
# user_repository.py
# format_date.py
# validate_email.py
```

### 関数設計

**単一責務の原則**:
```python
# ✅ 良い例: 単一の責務
def calculate_total_price(items: list[CartItem]) -> int:
    return sum(item.price * item.quantity for item in items)

def format_price(amount: int) -> str:
    return f"¥{amount:,}"

# ❌ 悪い例: 複数の責務
def calculate_and_format_price(items: list[CartItem]) -> str:
    total = sum(item.price * item.quantity for item in items)
    return f"¥{total:,}"
```

**関数の長さ**:
- 目標: 20行以内
- 推奨: 50行以内
- 100行以上: リファクタリングを検討

**パラメータの数**:
```python
# ✅ 良い例: dataclass でまとめる
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CreateTaskOptions:
    title: str
    description: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    due_date: datetime | None = None

async def create_task(options: CreateTaskOptions) -> Task:
    # 実装
    ...

# ❌ 悪い例: パラメータが多すぎる
async def create_task(
    title: str,
    description: str,
    priority: str,
    due_date: datetime,
    tags: list[str],
    assignee: str,
) -> Task: ...
```

### エラーハンドリング

**カスタム例外クラス**:
```python
# 例外クラスの定義
class AppError(Exception):
    """アプリケーション基底例外"""

class ValidationError(AppError):
    def __init__(self, message: str, field: str, value: object) -> None:
        super().__init__(message)
        self.field = field
        self.value = value

class NotFoundError(AppError):
    def __init__(self, resource: str, id: str) -> None:
        super().__init__(f"{resource} not found: {id}")
        self.resource = resource
        self.id = id

class DatabaseError(AppError):
    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.__cause__ = cause
```

**エラーハンドリングパターン**:
```python
# ✅ 良い例: 適切なエラーハンドリング
import logging

logger = logging.getLogger(__name__)

async def get_task(id: str) -> Task:
    try:
        task = await repository.find_by_id(id)

        if task is None:
            raise NotFoundError("Task", id)

        return task
    except NotFoundError:
        # 予期されるエラー: 適切に処理
        logger.warning("タスクが見つかりません: %s", id)
        raise
    except Exception as e:
        # 予期しないエラー: ラップして上位に伝播
        raise DatabaseError("タスクの取得に失敗しました", e) from e

# ❌ 悪い例: エラーを無視
async def get_task(id: str) -> Task | None:
    try:
        return await repository.find_by_id(id)
    except Exception:
        return None  # エラー情報が失われる
```

**エラーメッセージ**:
```python
# ✅ 良い例: 具体的で解決策を示す
raise ValidationError(
    f"タイトルは1-200文字で入力してください。現在の文字数: {len(title)}",
    "title",
    title,
)

# ❌ 悪い例: 曖昧で役に立たない
raise ValueError("Invalid input")
```

### 非同期処理

**async/await の使用**:
```python
# ✅ 良い例: async/await
async def fetch_user_tasks(user_id: str) -> list[Task]:
    try:
        user = await user_repository.find_by_id(user_id)
        tasks = await task_repository.find_by_user_id(user.id)
        return tasks
    except Exception:
        logger.exception("タスクの取得に失敗")
        raise

# ❌ 悪い例: 同期的なブロッキングI/O
def fetch_user_tasks(user_id: str) -> list[Task]:
    user = user_repository.find_by_id_sync(user_id)  # ブロッキング
    return task_repository.find_by_user_id_sync(user.id)
```

**並列処理**:
```python
import asyncio

# ✅ 良い例: asyncio.gather で並列実行
async def fetch_multiple_users(ids: list[str]) -> list[User]:
    return list(await asyncio.gather(*[
        user_repository.find_by_id(id) for id in ids
    ]))

# ❌ 悪い例: 逐次実行
async def fetch_multiple_users(ids: list[str]) -> list[User]:
    users: list[User] = []
    for id in ids:
        user = await user_repository.find_by_id(id)  # 遅い
        users.append(user)
    return users
```

## コメント規約

### ドキュメントコメント

**Google スタイル Docstring**:
```python
async def create_task(data: CreateTaskOptions) -> Task:
    """タスクを作成する。

    Args:
        data: 作成するタスクのデータ。

    Returns:
        作成されたタスク。

    Raises:
        ValidationError: データが不正な場合。
        DatabaseError: データベースエラーの場合。

    Example:
        >>> task = await create_task(CreateTaskOptions(title="新しいタスク"))
    """
    # 実装
    ...
```

### インラインコメント

**良いコメント**:
```python
# ✅ 理由を説明
# キャッシュを無効化して最新データを取得
cache.clear()

# ✅ 複雑なロジックを説明
# Kadane のアルゴリズムで最大部分配列和を計算
# 時間計算量: O(n)
max_so_far = arr[0]
max_ending_here = arr[0]

# ✅ TODO・FIXME を活用
# TODO: キャッシュ機能を実装 (Issue #123)
# FIXME: 大量データでパフォーマンス劣化 (Issue #456)
```

**悪いコメント**:
```python
# ❌ コードの内容を繰り返すだけ
# i を 1 増やす
i += 1

# ❌ コメントアウトされたコード (削除すべき)
# old_implementation = lambda: ...
```

## セキュリティ

### 入力検証

```python
import re

# ✅ 良い例: 厳密な検証
def validate_email(email: str) -> None:
    if not email or not isinstance(email, str):
        raise ValidationError("メールアドレスは必須です", "email", email)

    email_regex = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    if not email_regex.match(email):
        raise ValidationError("メールアドレスの形式が不正です", "email", email)

    if len(email) > 254:
        raise ValidationError("メールアドレスが長すぎます", "email", email)

# ❌ 悪い例: 検証なし
def validate_email(email: str) -> None:
    pass
```

### 機密情報の管理

```python
import os

# ✅ 良い例: 環境変数から読み込み
api_key = os.environ.get("API_KEY")
if not api_key:
    raise RuntimeError("API_KEY 環境変数が設定されていません")

# ❌ 悪い例: ハードコード
api_key = "sk-1234567890abcdef"  # 絶対にしない！
```

## パフォーマンス

### データ構造の選択

```python
# ✅ 良い例: dict で O(1) アクセス
user_map = {u.id: u for u in users}
user = user_map.get(user_id)  # O(1)

# ❌ 悪い例: リストで O(n) 検索
user = next((u for u in users if u.id == user_id), None)  # O(n)
```

### ループの最適化

```python
# ✅ 良い例: for-in ループ
for item in items:
    process(item)

# ✅ リスト内包表記
results = [process(item) for item in items]

# ❌ 悪い例: インデックスアクセスを乱用
for i in range(len(items)):
    process(items[i])
```

### メモ化

```python
from functools import lru_cache

# ✅ 良い例: lru_cache でメモ化
@lru_cache(maxsize=128)
def expensive_calculation(input: str) -> str:
    # 重い計算
    return result
```

## テストコード

### テストの構造 (Given-When-Then)

```python
import pytest
from unittest.mock import AsyncMock

class TestTaskService:
    async def test_create_task_with_valid_data(self) -> None:
        # Given: 準備
        mock_repository = AsyncMock()
        service = TaskService(mock_repository)
        task_data = CreateTaskOptions(
            title="テストタスク",
            description="テスト用の説明",
        )

        # When: 実行
        result = await service.create(task_data)

        # Then: 検証
        assert result is not None
        assert result.id is not None
        assert result.title == "テストタスク"
        assert result.description == "テスト用の説明"

    async def test_create_task_with_empty_title_raises_error(self) -> None:
        # Given: 準備
        mock_repository = AsyncMock()
        service = TaskService(mock_repository)
        invalid_data = CreateTaskOptions(title="")

        # When/Then: 実行と検証
        with pytest.raises(ValidationError):
            await service.create(invalid_data)
```

### モックの作成

```python
import pytest
from unittest.mock import AsyncMock

# ✅ 良い例: pytest fixture でモック
@pytest.fixture
def mock_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_id.return_value = None
    return repo

# テストごとに動作を設定
@pytest.fixture
def mock_repository_with_task(sample_task: Task) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_id.return_value = sample_task
    return repo
```

## リファクタリング

### マジックナンバーの排除

```python
# ✅ 良い例: 定数を定義
MAX_RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 1.0

import asyncio

for attempt in range(MAX_RETRY_COUNT):
    try:
        return await fetch_data()
    except Exception:
        if attempt < MAX_RETRY_COUNT - 1:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
        else:
            raise

# ❌ 悪い例: マジックナンバー
for attempt in range(3):
    try:
        return await fetch_data()
    except Exception:
        if attempt < 2:
            await asyncio.sleep(1.0)
```

### 関数の抽出

```python
# ✅ 良い例: 関数を抽出
def process_order(order: Order) -> None:
    _validate_order(order)
    _calculate_total(order)
    _apply_discounts(order)
    repository.save(order)

def _validate_order(order: Order) -> None:
    if not order.items:
        raise ValidationError("商品が選択されていません", "items", order.items)

def _calculate_total(order: Order) -> None:
    order.total = sum(item.price * item.quantity for item in order.items)

# ❌ 悪い例: 長い関数
def process_order(order: Order) -> None:
    if not order.items:
        raise ValidationError("商品が選択されていません", "items", order.items)

    order.total = sum(item.price * item.quantity for item in order.items)

    if order.coupon:
        order.total -= int(order.total * order.coupon.discount_rate)

    repository.save(order)
```

## チェックリスト

実装完了前に確認:

### コード品質
- [ ] 命名が明確で一貫している (snake_case)
- [ ] 関数が単一の責務を持っている
- [ ] マジックナンバーがない
- [ ] 型注釈が適切に記載されている
- [ ] エラーハンドリングが実装されている

### セキュリティ
- [ ] 入力検証が実装されている
- [ ] 機密情報がハードコードされていない
- [ ] 適切な例外クラスを使用している

### パフォーマンス
- [ ] 適切なデータ構造を使用している
- [ ] 不要な計算を避けている
- [ ] ループが最適化されている

### テスト
- [ ] ユニットテストが書かれている
- [ ] テストがパスする
- [ ] エッジケースがカバーされている

### ドキュメント
- [ ] 関数・クラスに Google スタイル Docstring がある
- [ ] 複雑なロジックにコメントがある
- [ ] TODO や FIXME が記載されている (該当する場合)

### ツール
- [ ] `uv run ruff check .` — Lint エラーがない
- [ ] `uv run mypy src` — 型チェックがパスする
- [ ] `uv run pytest` — テストがパスする
