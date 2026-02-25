# プロジェクトメモリ

## プロジェクト状態

本リポジトリは **Python（uv + FastAPI）版スペック駆動開発テンプレート**から派生した **AI討論アプリ（AI Debate）** の開発リポジトリです。

- MVP実装済み: ペルソナ設定・往復議論（SSEストリーミング）・Web検索（Tavily）・最終まとめ出力
- 永続ドキュメント（`docs/`）作成済み（PRD・機能設計・アーキテクチャ等6ファイル）
- Claude Code スキル群（ステアリング・add-feature等）利用可能

### 主要実装ファイル

- `src/app/routers/debate.py` - SSEエンドポイント
- `src/app/services/debate_orchestrator.py` - 議論進行制御
- `src/app/services/agent_runner.py` - 1エージェント実行（tool_useループ）
- `src/app/infra/web_search.py` - Tavily Web検索
- `src/app/infra/session_store.py` - セッション管理
- `src/app/static/index.html` - フロントエンド（Vanilla JS + SSE、単一ファイル）

## 技術スタック

- 開発環境: devcontainer
- Python 3.12
- パッケージマネージャー: uv
- Webフレームワーク: FastAPI
- テスト: pytest + pytest-asyncio
- Lint/Format: ruff
- 型チェック: mypy
- Gitフック: pre-commit

### 環境変数

`.env.example` を `.env` にコピーして `AWS_ACCESS_KEY_ID`・`AWS_SECRET_ACCESS_KEY`・`AWS_REGION`・`TAVILY_API_KEY` を設定する。

### よく使うコマンド

```bash
uv run pytest              # テスト実行
uv run ruff check .        # lintチェック
uv run ruff format .       # フォーマット
uv run mypy src            # 型チェック
uv run uvicorn app.main:app --app-dir src --reload  # 開発サーバー起動
```

## スペック駆動開発の基本原則

### 基本フロー

1. **ドキュメント作成**: 永続ドキュメント(`docs/`)で「何を作るか」を定義
2. **作業計画**: ステアリングファイル(`.steering/`)で「今回何をするか」を計画
3. **実装**: tasklist.mdに従って実装し、進捗を随時更新
4. **検証**: テストと動作確認
5. **更新**: 必要に応じてドキュメント更新

### 重要なルール

#### ドキュメント作成時

**1ファイルずつ作成し、必ずユーザーの承認を得てから次に進む**

承認待ちの際は、明確に伝える:
```
「[ドキュメント名]の作成が完了しました。内容を確認してください。
承認いただけたら次のドキュメントに進みます。」
```

#### 実装前の確認

新しい実装を始める前に、必ず以下を確認:

1. CLAUDE.mdを読む
2. 関連する永続ドキュメント(`docs/`)を読む
3. Grepで既存の類似実装を検索
4. 既存パターンを理解してから実装開始

#### ステアリングファイル管理

作業ごとに `.steering/[YYYYMMDD]-[タスク名]/` を作成:

- `requirements.md`: 今回の要求内容
- `design.md`: 実装アプローチ
- `tasklist.md`: 具体的なタスクリスト

命名規則: `YYYYMMDD-kebab-case-task-name` 形式（例: `20260224-add-question-tool`）

**作業計画・実装・検証時は`steering`スキルを使用してください。**

- **作業計画時**: `Skill('steering')`でモード1(ステアリングファイル作成)
- **実装時**: `Skill('steering')`でモード2(実装とtasklist.md更新管理)
- **検証時**: `Skill('steering')`でモード3(振り返り)

詳細な手順と更新管理のルールはsteeringスキル内に定義されています。

## ディレクトリ構造

### 永続的ドキュメント(`docs/`)

アプリケーション全体の「何を作るか」「どう作るか」を定義:

#### 下書き・アイデア（`docs/ideas/`）
- 壁打ち・ブレインストーミングの成果物
- 技術調査メモ
- 自由形式（構造化は最小限）
- `/setup-project`実行時に自動的に読み込まれる

#### 正式版ドキュメント
- **product-requirements.md** - プロダクト要求定義書
- **functional-design.md** - 機能設計書
- **architecture.md** - 技術仕様書
- **repository-structure.md** - リポジトリ構造定義書
- **development-guidelines.md** - 開発ガイドライン
- **glossary.md** - ユビキタス言語定義

### 作業単位のドキュメント(`.steering/`)

特定の開発作業における「今回何をするか」を定義:

- `requirements.md`: 今回の作業の要求内容
- `design.md`: 変更内容の設計
- `tasklist.md`: タスクリスト

## 開発プロセス

### 初回セットアップ（完了済み）

1. ~~このテンプレートを使用~~
2. ~~`/setup-project` で永続的ドキュメント作成~~ → 作成済み（`docs/`配下6ファイル）
3. `/add-feature [機能]` で機能実装 → MVP実装済み

### 日常的な使い方

**基本は普通に会話で依頼してください:**

```text
# ドキュメントの編集
> PRDに新機能を追加してください
> architecture.mdのパフォーマンス要件を見直して
> glossary.mdに新しいドメイン用語を追加

# 機能追加(定型フローはコマンド)
> /add-feature ユーザープロフィール編集

# 詳細レビュー(詳細なレポートが必要なとき)
> /review-docs docs/product-requirements.md
```

**ポイント**: スペック駆動開発の詳細を意識する必要はありません。Claude Codeが適切なスキルを判断してロードします。

