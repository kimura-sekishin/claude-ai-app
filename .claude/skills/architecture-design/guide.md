# アーキテクチャ設計ガイド

## 基本原則

### 1. 技術選定には理由を明記

**悪い例**:
```
- Python
- FastAPI
```

**良い例**:
```
- Python 3.12
  - 型ヒントの強化とパフォーマンス改善により、保守性と実行効率が向上
  - 広大なエコシステムにより、必要なライブラリの入手が容易
  - 科学計算・Web・CLIなど多様な用途に対応

- FastAPI 0.x
  - 型アノテーションをベースとした自動バリデーションとドキュメント生成
  - 非同期処理(async/await)に対応し、高いスループットを実現
  - OpenAPI仕様を自動生成し、フロントエンドとの連携が容易

- uv
  - Rustで実装された高速なパッケージマネージャー・プロジェクト管理ツール
  - pyproject.tomlによる依存関係の一元管理
  - 仮想環境の自動管理により、環境の再現性が高い
```

### 2. レイヤー分離の原則

各レイヤーの責務を明確にし、依存関係を一方向に保ちます:

```
UI → Service → Data (OK)
UI ← Service (NG)
UI → Data (NG)
```

### 3. 測定可能な要件

すべてのパフォーマンス要件は測定可能な形で記述します。

## レイヤードアーキテクチャの設計

### 各レイヤーの責務

**UIレイヤー**:
```python
# 責務: ユーザー入力の受付とバリデーション
class CLI:
    # OK: サービスレイヤーを呼び出す
    async def add_task(self, title: str) -> None:
        task = await self.task_service.create({"title": title})
        print(f"Created: {task.id}")

    # NG: データレイヤーを直接呼び出す
    async def add_task(self, title: str) -> None:
        task = await self.repository.save({"title": title})  # ❌
```

**サービスレイヤー**:
```python
# 責務: ビジネスロジックの実装
class TaskService:
    # ビジネスロジック: 優先度の自動推定
    async def create(self, data: CreateTaskData) -> Task:
        task = {
            **data,
            "estimated_priority": self._estimate_priority(data),
        }
        return await self.repository.save(task)
```

**データレイヤー**:
```python
# 責務: データの永続化
class TaskRepository:
    async def save(self, task: Task) -> None:
        await self.storage.write(task)
```

## パフォーマンス要件の設定

### 具体的な数値目標

```
コマンド実行時間: 100ms以内(平均的なPC環境で)
└─ 測定方法: time.perf_counter でCLI起動から結果表示まで計測
└─ 測定環境: CPU Core i5相当、メモリ8GB、SSD

タスク一覧表示: 1000件まで1秒以内
└─ 測定方法: 1000件のダミーデータで計測
└─ 許容範囲: 100件で100ms、1000件で1秒、10000件で10秒
```

## セキュリティ設計

### データ保護の3原則

1. **最小権限の原則**
```bash
# ファイルパーミッション
chmod 600 ~/.devtask/tasks.json  # 所有者のみ読み書き
```

2. **入力検証**
```python
def validate_title(title: str) -> None:
    if not title or len(title) == 0:
        raise ValidationError("タイトルは必須です")
    if len(title) > 200:
        raise ValidationError("タイトルは200文字以内です")
```

3. **機密情報の管理**
```bash
# 環境変数で管理
export DEVTASK_API_KEY="xxxxx"  # コード内にハードコードしない
```

## スケーラビリティ設計

### データ増加への対応

**想定データ量**: [例: 10,000件のタスク]

**対策**:
- データのページネーション
- 古いデータのアーカイブ
- インデックスの最適化

```python
# アーカイブ機能の例: 古いタスクを別ファイルに移動
from datetime import datetime

class ArchiveService:
    async def archive_completed_tasks(self, older_than: datetime) -> None:
        old_tasks = await self.repository.find_completed(older_than)
        await self.archive_storage.save(old_tasks)
        await self.repository.delete_many([t.id for t in old_tasks])
```

## 依存関係管理

### バージョン管理方針

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi>=0.100.0",      # マイナーバージョンアップは自動
    "httpx==0.27.0",         # 破壊的変更のリスクがある場合は固定
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "ruff>=0.4.0",
    "mypy>=1.9.0",
]
```

**方針**:
- 安定版は下限固定(>=でマイナーバージョンアップを許可)
- 破壊的変更のリスクがある場合は完全固定(==)
- 開発依存はuv add --devで管理し、pyproject.tomlに記録

### パッケージ追加コマンド

```bash
uv add fastapi          # 本番依存を追加
uv add --dev pytest     # 開発依存を追加
uv run pytest           # テスト実行
uv run ruff check .     # lintチェック
```

## インターフェース設計

### Protocol と TypedDict の活用

```python
# ✅ Protocol: 振る舞いの定義(依存性逆転の原則)
from typing import Protocol

class ITaskRepository(Protocol):
    async def save(self, task: "Task") -> None: ...
    async def find_by_id(self, task_id: str) -> "Task | None": ...

# ✅ TypedDict: データ構造の定義
from typing import TypedDict

class CreateTaskData(TypedDict):
    title: str
    description: str | None
    priority: int

# ✅ 型アノテーション付きクラス
from dataclasses import dataclass

@dataclass
class Task:
    id: str
    title: str
    description: str | None = None
    priority: int = 0
```

## チェックリスト

- [ ] すべての技術選定に理由が記載されている
- [ ] レイヤードアーキテクチャが明確に定義されている
- [ ] パフォーマンス要件が測定可能である
- [ ] セキュリティ考慮事項が記載されている
- [ ] スケーラビリティが考慮されている
- [ ] バックアップ戦略が定義されている
- [ ] 依存関係管理のポリシーが明確である
- [ ] テスト戦略が定義されている
