# 開発ガイドライン (Development Guidelines)

## コーディング規約

### 命名規則

#### 変数・関数

**Python**:
```python
# ✅ 良い例
user_profile_data = fetch_user_profile()
def calculate_total_price(items: list[CartItem]) -> int: ...

# ❌ 悪い例
data = fetch()
def calc(arr: list) -> int: ...
```

**原則**:
- 変数: snake_case、名詞または名詞句
- 関数: snake_case、動詞で始める
- 定数: UPPER_SNAKE_CASE
- Boolean: `is_`, `has_`, `should_`で始める

#### クラス・型エイリアス

```python
# クラス: PascalCase、名詞
class TaskManager: ...
class UserAuthenticationService: ...

# TypedDict: PascalCase
from typing import TypedDict

class Task(TypedDict):
    id: str
    title: str

# Literal型
from typing import Literal
TaskStatus = Literal['todo', 'in_progress', 'completed']
```

### コードフォーマット

**インデント**: 4スペース

**行の長さ**: 最大[80/100/120]文字

**例**:
```python
# Python コードフォーマット例
[コード例]
```

### コメント規約

**関数・クラスのドキュメント**:
```python
def count_tasks(
    tasks: list[Task],
    filter: TaskFilter | None = None,
) -> int:
    """タスクの合計数を計算する。

    Args:
        tasks: 計算対象のタスクリスト
        filter: フィルター条件(オプション)

    Returns:
        タスクの合計数

    Raises:
        ValueError: タスクリストが不正な場合
    """
    # 実装
```

**インラインコメント**:
```python
# ✅ 良い例: なぜそうするかを説明
# キャッシュを無効化して、最新データを取得
cache.clear()

# ❌ 悪い例: 何をしているか(コードを見れば分かる)
# キャッシュをクリアする
cache.clear()
```

### エラーハンドリング

**原則**:
- 予期されるエラー: 適切なエラークラスを定義
- 予期しないエラー: 上位に伝播
- エラーを無視しない

**例**:
```python
# エラークラス定義
class ValidationError(Exception):
    def __init__(self, message: str, field: str, value: object) -> None:
        super().__init__(message)
        self.field = field
        self.value = value

# エラーハンドリング
try:
    task = await task_service.create(data)
except ValidationError as error:
    print(f"検証エラー [{error.field}]: {error}")
    # ユーザーにフィードバック
except Exception as error:
    print(f"予期しないエラー: {error}")
    raise  # 上位に伝播
```

## Git運用ルール

### ブランチ戦略

**ブランチ種別**:
- `main`: 本番環境にデプロイ可能な状態
- `develop`: 開発の最新状態
- `feature/[機能名]`: 新機能開発
- `fix/[修正内容]`: バグ修正
- `refactor/[対象]`: リファクタリング

**フロー**:
```
main
  └─ develop
      ├─ feature/task-management
      ├─ feature/user-auth
      └─ fix/task-validation
```

### コミットメッセージ規約

**フォーマット**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: コードフォーマット
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: ビルド、補助ツール等

**例**:
```
feat(task): タスクの優先度設定機能を追加

ユーザーがタスクに優先度(高/中/低)を設定できるようにしました。
- Taskモデルにpriorityフィールドを追加
- CLIに--priorityオプションを追加
- 優先度によるソート機能を実装

Closes #123
```

### プルリクエストプロセス

**作成前のチェック**:
- [ ] 全てのテストがパス
- [ ] Lintエラーがない
- [ ] 型チェックがパス
- [ ] 競合が解決されている

**PRテンプレート**:
```markdown
## 概要
[変更内容の簡潔な説明]

## 変更理由
[なぜこの変更が必要か]

## 変更内容
- [変更点1]
- [変更点2]

## テスト
- [ ] ユニットテスト追加
- [ ] 手動テスト実施

## スクリーンショット(該当する場合)
[画像]

## 関連Issue
Closes #[Issue番号]
```

**レビュープロセス**:
1. セルフレビュー
2. 自動テスト実行
3. レビュアーアサイン
4. レビューフィードバック対応
5. 承認後マージ

## テスト戦略

### テストの種類

#### ユニットテスト

**対象**: 個別の関数・クラス

**カバレッジ目標**: [80/90/100]%

**例**:
```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
class TestTaskService:
    class TestCreate:
        async def test_正常なデータでタスクを作成できる(self):
            service = TaskService(mock_repository)
            task = await service.create(
                title="テストタスク",
                description="説明",
            )

            assert task.id is not None
            assert task.title == "テストタスク"

        async def test_タイトルが空の場合ValidationErrorを送出する(self):
            service = TaskService(mock_repository)

            with pytest.raises(ValidationError):
                await service.create(title="")
```

#### 統合テスト

**対象**: 複数コンポーネントの連携

**例**:
```python
@pytest.mark.asyncio
async def test_タスクのCRUDができる():
    # 作成
    created = await task_service.create(title="テスト")

    # 取得
    found = await task_service.find_by_id(created.id)
    assert found.title == "テスト"

    # 更新
    await task_service.update(created.id, title="更新後")
    updated = await task_service.find_by_id(created.id)
    assert updated.title == "更新後"

    # 削除
    await task_service.delete(created.id)
    deleted = await task_service.find_by_id(created.id)
    assert deleted is None
```

#### E2Eテスト

**対象**: ユーザーシナリオ全体

**例**:
```python
@pytest.mark.asyncio
async def test_ユーザーがタスクを追加して完了できる(client):
    # タスク追加
    response = await client.post("/tasks", json={"title": "新しいタスク"})
    assert response.status_code == 201
    assert response.json()["title"] == "新しいタスク"

    task_id = response.json()["id"]

    # タスク一覧表示
    list_response = await client.get("/tasks")
    titles = [t["title"] for t in list_response.json()]
    assert "新しいタスク" in titles

    # タスク完了
    done_response = await client.patch(f"/tasks/{task_id}", json={"status": "completed"})
    assert done_response.status_code == 200
```

### テスト命名規則

**パターン**: `test_[条件]_[期待結果]` または日本語で記述

**例**:
```python
# ✅ 良い例
def test_create_empty_title_raises_validation_error(): ...
def test_find_by_id_existing_id_returns_task(): ...
def test_delete_nonexistent_id_raises_not_found_error(): ...

# または日本語
def test_空タイトルでValueErrorが発生する(): ...
def test_存在するIDでタスクを取得できる(): ...

# ❌ 悪い例
def test1(): ...
def test_works(): ...
def test_should_work_correctly(): ...
```

### モック・スタブの使用

**原則**:
- 外部依存(API、DB、ファイルシステム)はモック化
- ビジネスロジックは実装を使用

**例**:
```python
from unittest.mock import AsyncMock, MagicMock

# リポジトリをモック化
mock_repository = MagicMock()
mock_repository.save = AsyncMock()
mock_repository.find_by_id = AsyncMock()
mock_repository.find_all = AsyncMock()
mock_repository.delete = AsyncMock()

# サービスは実際の実装を使用
service = TaskService(mock_repository)
```

## コードレビュー基準

### レビューポイント

**機能性**:
- [ ] 要件を満たしているか
- [ ] エッジケースが考慮されているか
- [ ] エラーハンドリングが適切か

**可読性**:
- [ ] 命名が明確か
- [ ] コメントが適切か
- [ ] 複雑なロジックが説明されているか

**保守性**:
- [ ] 重複コードがないか
- [ ] 責務が明確に分離されているか
- [ ] 変更の影響範囲が限定的か

**パフォーマンス**:
- [ ] 不要な計算がないか
- [ ] メモリリークの可能性がないか
- [ ] データベースクエリが最適化されているか

**セキュリティ**:
- [ ] 入力検証が適切か
- [ ] 機密情報がハードコードされていないか
- [ ] 権限チェックが実装されているか

### レビューコメントの書き方

**建設的なフィードバック**:
```markdown
## ✅ 良い例
この実装だと、タスク数が増えた時にパフォーマンスが劣化する可能性があります。
代わりに、インデックスを使った検索を検討してはどうでしょうか？

## ❌ 悪い例
この書き方は良くないです。
```

**優先度の明示**:
- `[必須]`: 修正必須
- `[推奨]`: 修正推奨
- `[提案]`: 検討してほしい
- `[質問]`: 理解のための質問

## 開発環境セットアップ

### 必要なツール

| ツール | バージョン | インストール方法 |
|--------|-----------|-----------------|
| Python | 3.12以上 | https://python.org |
| uv | 最新 | `curl -Ls https://astral.sh/uv/install.sh | sh` |

### セットアップ手順

```bash
# 1. リポジトリのクローン
git clone [URL]
cd [project-name]

# 2. 依存関係のインストール
uv sync

# 3. 環境変数の設定
cp .env.example .env
# .envファイルを編集

# 4. 開発サーバーの起動
uv run uvicorn src.app.main:app --reload
```

### よく使うコマンド

```bash
uv run pytest              # テスト実行
uv run ruff check .        # lintチェック
uv run ruff format .       # フォーマット
uv run mypy src            # 型チェック
```

### 推奨開発ツール(該当する場合)

- [ツール1]: [説明]
- [ツール2]: [説明]
