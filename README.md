# AI討論 / AI Debate

2つのAIペルソナがリアルタイムでWeb検索を使いながら議論するWebアプリです。

本リポジトリは[「実践Claude Code入門 - 現場で活用するためのAIコーディングの思考法」](https://www.amazon.co.jp/dp/4297153548)（技術評論社）のサンプルコードです。スペック駆動開発の実践例として実装されています。

---

## 機能

- **ペルソナ設定**: 2つのAIキャラクターの名前・立場を設定（省略時はデフォルトを使用）
- **テーマ入力**: 議論させたいトピックを自由に設定
- **リアルタイム議論**: SSE（Server-Sent Events）でAIの発言をストリーミング表示
- **Web検索ツール**: AIが自律的にTavily APIで検索し、根拠を持って議論
- **議論まとめ**: 全ターン終了後に両者の主張と結論を自動生成

## 技術スタック

| 分類 | 技術 |
|------|------|
| バックエンド | Python 3.12 + FastAPI |
| LLM | claude-sonnet-4-6 (AWS Bedrock) |
| Web検索 | Tavily API |
| フロントエンド | Vanilla HTML/CSS/JS |
| リアルタイム通信 | Server-Sent Events |

---

## 前提条件

- Docker（Dev Container使用時）
- AWS アカウント（Bedrock の `bedrock:InvokeModel` 権限付き IAM ユーザーまたはロール）
- [Tavily](https://tavily.com) の API キー
- AWS Bedrock で `claude-sonnet-4-6` のモデルアクセスを有効化済み（[AWS コンソール > Bedrock > モデルアクセス](https://console.aws.amazon.com/bedrock/home#/modelaccess) から申請）

---

## セットアップ

### 1. Dev Containerで開く（推奨）

Visual Studio Codeで「Reopen in Container」を選択すると、以下が自動でセットアップされます：

- Python 3.12 環境の構築
- `uv sync` による依存関係インストール
- pre-commit フックの登録

> Dockerのインストールが事前に必要です。

**Dev Containerを使わない場合（Python 3.12以上が必要）:**

```bash
pip install uv
uv sync
uv run pre-commit install
```

### 2. 環境変数を設定

```bash
cp .env.example .env
```

`.env` を編集して認証情報を入力してください：

```
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_REGION=us-east-1
TAVILY_API_KEY=<your-key>    # https://app.tavily.com でサインアップして取得
```

### 3. 開発サーバーを起動

```bash
uv run uvicorn app.main:app --app-dir src --reload
```

ブラウザで http://localhost:8000 にアクセスしてください。

---

## 開発コマンド

```bash
uv run pytest              # テスト実行
uv run ruff check .        # Lint チェック
uv run mypy src            # 型チェック
uv run ruff format .       # フォーマット
```

---

## プロジェクト構成

```
src/app/
├── main.py                  # FastAPIアプリ起動・静的ファイル配信
├── routers/
│   └── debate.py               # APIエンドポイント (POST /start, GET /stream)
├── services/
│   ├── debate_orchestrator.py  # 議論全体の進行管理
│   └── agent_runner.py         # 1ペルソナ1ターンのエージェント実行
├── infra/
│   ├── session_store.py        # インメモリセッション管理
│   └── web_search.py           # Tavily Web検索ツール
├── models/
│   ├── debate.py               # データモデル定義
│   └── errors.py               # エラークラス定義
└── static/index.html           # フロントエンド（単一ファイル）
```

---

## デプロイ (AWS App Runner)

### 前提条件

- AWS CLI がセットアップ済み
- AWS Bedrock で `claude-haiku-4-5-20251001` のモデルアクセスを有効化済み

### 1. IAM ロールの作成

App Runner から Bedrock を呼び出すためのインスタンスロールを作成します。

**信頼ポリシー** (App Runner サービスプリンシパルを信頼):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**アタッチするポリシー** (Bedrock へのモデル呼び出し権限):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "bedrock:InvokeModel",
    "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude*"
  }]
}
```

### オプション A: コンテナ (ECR) デプロイ

**1. ECR リポジトリを作成**
```bash
aws ecr create-repository --repository-name ai-debate --region us-east-1
```

**2. Docker ビルド & ECR へプッシュ**
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/ai-debate"

docker build -t ai-debate .
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com"
docker tag ai-debate:latest "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"
```

**3. App Runner サービスを作成 ([コンソール](https://console.aws.amazon.com/apprunner))**

| 項目 | 設定値 |
|------|-------|
| ソース | Amazon ECR（上記でプッシュしたイメージ） |
| ポート | `8000` |
| インスタンスロール | 手順1で作成した IAM ロール |
| 環境変数 | `AWS_REGION=us-east-1`、`TAVILY_API_KEY=<your-key>` |
| **リクエストタイムアウト** | **`3600` 秒**（SSE の長時間接続に必須） |

> `AWS_ACCESS_KEY_ID` と `AWS_SECRET_ACCESS_KEY` はインスタンスロールで認証するため設定不要です。

### オプション B: GitHub ソースデプロイ (apprunner.yaml)

コンテナビルド不要で、GitHub リポジトリから直接デプロイできます。
[App Runner コンソール](https://console.aws.amazon.com/apprunner)で GitHub リポジトリを連携すると `apprunner.yaml` が自動読み込みされます。

コンソールで以下を追加設定してください:

| 項目 | 設定値 |
|------|-------|
| インスタンスロール | 手順1で作成した IAM ロール |
| 環境変数 | `TAVILY_API_KEY=<your-key>` を追加 |
| **リクエストタイムアウト** | **`3600` 秒**（SSE の長時間接続に必須） |

---

## ドキュメント

| ファイル | 内容 |
|---------|------|
| [docs/product-requirements.md](docs/product-requirements.md) | プロダクト要求定義書 |
| [docs/functional-design.md](docs/functional-design.md) | 機能設計書（SSEイベント・API設計） |
| [docs/architecture.md](docs/architecture.md) | 技術仕様書 |
| [docs/repository-structure.md](docs/repository-structure.md) | リポジトリ構造定義書 |
| [docs/development-guidelines.md](docs/development-guidelines.md) | 開発ガイドライン |
| [docs/glossary.md](docs/glossary.md) | ユビキタス言語定義（用語集） |

書籍・コードに関するご質問は [GenerativeAgents/claude-code-book](https://github.com/GenerativeAgents/claude-code-book) のイシューへ。
