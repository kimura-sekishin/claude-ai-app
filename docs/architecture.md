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
| uvicorn[standard] | >=0.32.0 | ASGIサーバー | FastAPIのデフォルト実行環境・高速 |
| anthropic[bedrock] | >=0.83.0 | LLM呼び出し（AWS Bedrock経由） | AnthropicBedrock clientでBedrock対応・tool_use APIが直感的 |
| sse-starlette | >=3.2.0 | Server-Sent Events配信 | FastAPIとの統合が容易・軽量 |
| tavily-python | >=0.7.21 | Web検索ツール実装 | LLM向け設計・JSON形式で検索結果取得 |
| pydantic | >=2.0.0 | リクエスト/レスポンスのバリデーション | FastAPIに統合済み・型安全 |
| python-dotenv | >=1.2.1 | 環境変数の読み込み | .envファイルで認証情報を管理 |

### 開発ツール

| 技術 | バージョン | 用途 | 選定理由 |
|------|-----------|------|----------|
| pytest | >=8.0.0 | テストフレームワーク | Pythonの標準的なテストツール |
| pytest-asyncio | >=0.24.0 | 非同期テスト | FastAPI/asyncioの非同期コードをテスト |
| pytest-cov | >=7.0.0 | カバレッジ計測 | カバレッジ目標の達成度を測定 |
| ruff | >=0.8.0 | Lint・フォーマット | 高速・ruff checkとruff formatで一元管理 |
| mypy | >=1.13.0 | 型チェック | 静的型解析でバグを早期発見 |
| pre-commit | >=4.0.0 | Gitフック管理 | コミット前に自動でLint・フォーマットを実行 |

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
│  DebateService / DebateOrchestrator / AgentRunner │
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
- **責務**: HTTPリクエストの受付・バリデーション、SSEイベントストリームの管理
- **許可される操作**: サービスレイヤーの呼び出し、SSEイベントの配信（各発言は全文を1イベントとして送信する非ストリーミング方式）
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
| 議論開始（初回tokenイベント） | 3秒以内 | SSEで最初のtokenイベントが届くまで（発言全文を1イベントとして送信） |
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

AWS認証は2つの方式に対応している:

**方式1: IAMロール（本番推奨）**

AWS App RunnerなどIAMロールが自動適用される環境では、アクセスキーの設定は不要。
`AsyncAnthropicBedrock` はAWS SDKの認証チェーンを自動的に使用する。

```bash
# .env（Gitに含めない・.gitignoreに追加）
AWS_REGION=us-east-1
TAVILY_API_KEY=xxxxx
```

**方式2: アクセスキー（ローカル開発時）**

```bash
# .env（Gitに含めない・.gitignoreに追加）
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
AWS_REGION=us-east-1
TAVILY_API_KEY=xxxxx
```

```python
# Bedrockクライアントの初期化（リージョンのみ指定、認証はAWS SDKに委譲）
import anthropic, os

client = anthropic.AsyncAnthropicBedrock(
    aws_region=os.environ.get("AWS_REGION", "us-east-1"),
)
```

### 入力検証

Pydanticスキーマでサーバーサイドバリデーションを実施。

```python
from pydantic import BaseModel, Field

class PersonaInput(BaseModel):
    # 省略可能（空欄時はデフォルトのペルソナ名・立場を使用）
    name: str = Field(default="", max_length=50)
    description: str = Field(default="", max_length=200)

class DebateStartRequest(BaseModel):
    persona_a: PersonaInput = Field(default_factory=PersonaInput)
    persona_b: PersonaInput = Field(default_factory=PersonaInput)
    theme: str = Field(min_length=1, max_length=200)
    max_turns: int = Field(default=2, ge=1, le=6)
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

### デプロイ構成

| 環境 | 方式 | 設定ファイル |
|------|------|-------------|
| ローカル開発 | uvicorn --reload | - |
| 本番（AWS） | AWS App Runner | `apprunner.yaml` |

- コンテナイメージは `Dockerfile` でビルドしECRにプッシュ（`scripts/deploy-ecr.ps1`）
- AWS App RunnerがTLS終端を自動処理するためHTTPS対応は追加設定不要

### Post-MVPの拡張方針

- セッション永続化: Redis or SQLiteに移行
- 同時実行制御: セマフォによるBedrock API呼び出し数の制限

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
AWSリージョン: us-east-1（クロスリージョン推論プロファイル使用のため）
必要なモデルアクセス: claude-haiku-4-5（Bedrockコンソールで有効化が必要）
使用するモデルID: us.anthropic.claude-haiku-4-5-20251001-v1:0（クロスリージョン推論プロファイル）
IAMポリシー:
  - bedrock:InvokeModel
  - bedrock:InvokeModelWithResponseStream
```

### コスト管理（デモ用途）
- Claude claude-haiku-4-5 の入出力トークン数はデモ用途のため都度管理しない
- Web検索APIはTavily無料枠（月1,000リクエスト）で十分

---

## 依存関係管理

```toml
# pyproject.toml の dependencies セクション
[project]
dependencies = [
    "anthropic[bedrock]>=0.83.0",
    "fastapi>=0.115.0",
    "python-dotenv>=1.2.1",
    "sse-starlette>=3.2.0",
    "tavily-python>=0.7.21",
    "uvicorn[standard]>=0.32.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0.0",
    "pytest-cov>=7.0.0",
]
```

**バージョン管理方針**:
- 安定ライブラリは `>=` で下限固定（マイナーバージョンアップを許可）
- 破壊的変更リスクがあるものは `==` で完全固定
- パッケージ追加: `uv add [package]`（本番）/ `uv add --dev [package]`（開発）
