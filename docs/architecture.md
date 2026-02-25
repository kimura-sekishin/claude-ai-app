# 技術仕様書 (Architecture Design Document)

## テクノロジースタック

### 言語・ランタイム

| 技術 | バージョン |
|------|-----------|
| Python | 3.12 |
| uv | latest |

### フレームワーク・ライブラリ

| 技術 | バージョン | 用途 | 選定理由 |
|------|-----------|------|----------|
| fastapi | >=0.115.0 | WebフレームワークとAPIサーバー | 非同期処理・Pydantic統合・SSE対応 |
| uvicorn | >=0.30.0 | ASGIサーバー | FastAPIのデフォルト実行環境・高速 |
| anthropic | >=0.40.0 | LLM呼び出し（AWS Bedrock経由） | AnthropicBedrock clientでBedrock対応・tool_use APIが直感的 |
| sse-starlette | >=2.0.0 | Server-Sent Events配信 | FastAPIとの統合が容易・軽量 |
| tavily-python | >=0.3.0 | Web検索ツール実装 | LLM向け設計・JSON形式で検索結果取得 |
| pydantic | >=2.0.0 | リクエスト/レスポンスのバリデーション | FastAPIに統合済み・型安全 |
| python-dotenv | >=1.0.0 | 環境変数の読み込み | .envファイルで認証情報を管理 |

### 開発ツール

| 技術 | バージョン | 用途 | 選定理由 |
|------|-----------|------|----------|
| pytest | >=8.0.0 | テストフレームワーク | Pythonの標準的なテストツール |
| pytest-asyncio | >=0.23.0 | 非同期テスト | FastAPI/asyncioの非同期コードをテスト |
| ruff | >=0.4.0 | Lint・フォーマット | 高速・ruff checkとruff formatで一元管理 |
| mypy | >=1.9.0 | 型チェック | 静的型解析でバグを早期発見 |

---

## アーキテクチャパターン

### レイヤードアーキテクチャ

```
┌──────────────────────────────────────────────────┐
│  プレゼンテーション層                               │
│  HTML/CSS/JavaScript + SSE クライアント            │
├──────────────────────────────────────────────────┤
│  APIレイヤー（FastAPI Router / Pydantic Schema）   │
│  HTTPリクエスト受付・バリデーション・SSE配信         │
├──────────────────────────────────────────────────┤
│  サービスレイヤー                                  │
│  DebateOrchestrator / AgentRunner                │
│  議論制御・エージェント実行・ビジネスロジック          │
├──────────────────────────────────────────────────┤
│  インフラレイヤー                                  │
│  BedrockClient / WebSearchTool / SessionStore    │
│  外部API呼び出し・セッション管理                    │
└──────────────────────────────────────────────────┘
```

#### プレゼンテーション層
- **責務**: ペルソナ設定フォームの表示・入力収集、SSEイベントを受け取って議論をリアルタイム描画
- **許可される操作**: APIレイヤーへのHTTPリクエスト、SSE接続
- **禁止される操作**: サービスレイヤーへの直接アクセス

#### APIレイヤー
- **責務**: HTTPリクエストの受付・バリデーション、SSEストリームの管理
- **許可される操作**: サービスレイヤーの呼び出し、SSEイベントの配信
- **禁止される操作**: ビジネスロジックの実装、外部APIの直接呼び出し

#### サービスレイヤー
- **責務**: 議論の進行制御、エージェントの実行、tool_useループ管理
- **許可される操作**: インフラレイヤーの呼び出し
- **禁止される操作**: HTTPレスポンスの直接操作、プレゼンテーション層への依存

#### インフラレイヤー
- **責務**: AWS Bedrock経由のClaude呼び出し、Tavily Web検索、セッションの一時保存
- **許可される操作**: 外部API呼び出し、メモリ上のデータ管理
- **禁止される操作**: ビジネスロジックの実装

---

## データ永続化戦略

MVPではデータベースを使用せず、**インメモリ（Pythonのdict）**でセッションを管理する。

### ストレージ方式

| データ種別 | ストレージ | フォーマット | 理由 |
|-----------|----------|-------------|------|
| DebateSession（実行中） | オンメモリ（dict） | Pythonオブジェクト | MVPに最適・DB不要・シンプル |
| SSEイベントキュー | asyncio.Queue | Pythonオブジェクト | 非同期ストリーミングに最適 |
| 議論履歴（永続化） | なし（MVP対象外） | - | Post-MVPで検討 |

### セッション管理

```python
# インメモリセッションストア（アプリ起動中のみ保持）
sessions: dict[str, DebateSession] = {}
event_queues: dict[str, asyncio.Queue] = {}
```

- サーバー再起動でセッションは消える（デモ用途のため許容）
- 同時接続数はデモ想定でシングルユーザー（Post-MVPでスケール対応）

---

## パフォーマンス要件

### レスポンスタイム

| 操作 | 目標時間 | 測定方法 |
|------|---------|---------|
| トップページ表示 | 2秒以内 | ブラウザのDevTools Network |
| 議論開始（初回トークン） | 3秒以内 | SSEで最初のtokenイベントが届くまで |
| Web検索ツール実行 | 10秒以内 | tool_startからtool_endイベントまで |
| 1ターンの発言完了 | 30秒以内 | turn_startからturn_endイベントまで |

### リソース使用量

| リソース | 上限 | 理由 |
|---------|------|------|
| メモリ | 512MB | デモ用のシングルユーザー想定 |
| 同時セッション数 | 5 | デモ用途・Bedrock APIコスト管理 |

---

## セキュリティアーキテクチャ

### 機密情報管理

すべての認証情報は環境変数で管理し、ソースコードにハードコードしない。

```bash
# .env（Gitに含めない・.gitignoreに追加）
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_REGION=us-east-1
TAVILY_API_KEY=xxxxx
```

```python
# 読み込み方法
from dotenv import load_dotenv
import os

load_dotenv()
aws_access_key = os.environ["AWS_ACCESS_KEY_ID"]  # 存在しなければ起動時にエラー
```

### 入力検証

Pydanticスキーマでサーバーサイドバリデーションを実施。

```python
from pydantic import BaseModel, Field

class PersonaInput(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=200)

class DebateStartRequest(BaseModel):
    persona_a: PersonaInput
    persona_b: PersonaInput
    theme: str = Field(min_length=1, max_length=200)
```

### プロンプトインジェクション対策

- ユーザー入力（ペルソナ名・テーマ）はシステムプロンプトに直接埋め込まない
- ユーザー入力は`{}`で囲まれた変数として扱い、安全なテンプレートに挿入する

---

## スケーラビリティ設計

### MVPの制約（許容する）

- インメモリセッション → サーバー再起動でリセット
- シングルプロセス → 水平スケールなし
- APIキー1セット → コスト管理のため同時実行数を制限

### Post-MVPの拡張方針

- セッション永続化: Redis or SQLiteに移行
- 同時実行制御: セマフォによるBedrock API呼び出し数の制限
- デプロイ: Railway / Render などのPaaS → 必要に応じてECS/Cloud Runへ

---

## テスト戦略

### ユニットテスト
- **フレームワーク**: pytest + pytest-asyncio
- **対象**: `WebSearchTool`、入力バリデーション、`DebateOrchestrator`のターン管理ロジック
- **モック方針**: Bedrock呼び出しと外部API呼び出しはすべてモック化
- **カバレッジ目標**: サービスレイヤー 80%以上

### 統合テスト
- **方法**: FastAPIの`TestClient` + `httpx.AsyncClient`
- **対象**: `/api/debate/start` の正常系・バリデーションエラー系

### 手動デモテスト
- ブラウザで実際に議論を完走させる（Web検索が発動することを確認）
- ストリーミング表示が途切れないことを確認
- エラー時のメッセージ表示を確認

```bash
# テスト実行
uv run pytest              # 全テスト
uv run pytest tests/unit/  # ユニットテストのみ
uv run pytest -v --tb=short  # 詳細表示
```

---

## 技術的制約

### 環境要件
- **OS**: Linux / macOS（devcontainer推奨）
- **Python**: 3.12以上
- **必要な外部依存**: AWS Bedrockアクセス権限（IAMポリシー: bedrock:InvokeModel）、Tavily APIキー

### Bedrock利用要件

```
AWSリージョン: us-east-1 または ap-northeast-1
必要なモデルアクセス: claude-sonnet-4-6（Bedrockコンソールで有効化が必要）
IAMポリシー:
  - bedrock:InvokeModel
  - bedrock:InvokeModelWithResponseStream
```

### コスト管理（デモ用途）
- Claude claude-sonnet-4-6 の入出力トークン数はデモ用途のため都度管理しない
- Web検索APIはTavily無料枠（月1,000リクエスト）で十分

---

## 依存関係管理

```toml
# pyproject.toml の dependencies セクション
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "anthropic>=0.40.0",
    "sse-starlette>=2.0.0",
    "tavily-python>=0.3.0",
    "python-dotenv>=1.0.0",
]

[tool.uv.dev-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
    "mypy>=1.9.0",
]
```

**バージョン管理方針**:
- 安定ライブラリは `>=` で下限固定（マイナーバージョンアップを許可）
- 破壊的変更リスクがあるものは `==` で完全固定
- パッケージ追加: `uv add [package]`（本番）/ `uv add --dev [package]`（開発）
