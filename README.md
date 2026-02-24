# claude-code-python

本リポジトリは技術評論社より発行されている[「実践Claude Code入門 - 現場で活用するためのAIコーディングの思考法」](https://www.amazon.co.jp/dp/4297153548)のサンプルコードからPython版テンプレートを構築したものです。

リポジトリ内のコード・プロンプトに関する詳細な解説は、書籍をご覧ください。

## テンプレートの概要

**Python（uv + FastAPI）を使ったスペック駆動開発**の練習・テンプレート環境です。

### 含まれるもの

- **FastAPI アプリケーションの骨格** (`src/app/main.py`)
- **pytest によるテスト環境** (`tests/`)
- **開発ツール設定**: ruff（Lint/Format）、mypy（型チェック）、pre-commit（Git フック）
- **Claude Code スキル群** (`.claude/skills/`)
  - PRD・機能設計書・アーキテクチャ設計書作成スキル
  - リポジトリ構造・開発ガイドライン・用語集作成スキル
  - ステアリング（作業計画）スキル
- **スペック駆動開発コマンド**
  - `/setup-project` - 永続ドキュメント一式を対話的に作成
  - `/add-feature [機能名]` - 機能追加
  - `/review-docs [ファイルパス]` - ドキュメントレビュー

### 最初にやること

Dev Container を開いたら、Claude Code に以下を実行してください：

```
/setup-project
```

対話形式で6つの永続ドキュメント（PRD・機能設計書・アーキテクチャ等）が `docs/` に作成されます。

書籍の内容に関するご質問、不備のご指摘については以下のリポジトリのイシューよりお願いいたします。

https://github.com/GenerativeAgents/claude-code-book

## テンプレートから新しいアプリを作るときのチェックリスト

このテンプレートから個別アプリを開発する際、以下のファイルに含まれる `claude-code-python` を実際のアプリ名に変更してください。

- [ ] [pyproject.toml](pyproject.toml) - `name = "claude-code-python"`
- [ ] [src/app/main.py](src/app/main.py) - `FastAPI(title="claude-code-python", ...)`
- [ ] [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) - `"name": "claude-code-python"`
- [ ] [README.md](README.md) - 本ファイルをアプリ用の内容に書き換え

上記3ファイルを変更後、ロックファイルを再生成してください：

```bash
uv lock
```

## 注意事項

本リポジトリの内容は読者からのフィードバックを受けて、より性能の良いプロンプトに変更されることがあります。差分は随時書籍に反映されますが、お手元の版との差分があることをご承知おきください。

## 使い方

### 1. リポジトリのクローン

```bash
git clone [このリポジトリ] claude-code-python
cd claude-code-python
```

### 2. Dev Container経由で開く

Visual Studio Codeで「Reopen in Container」を選択すると、自動的に次のように環境構築が行われます。

- Python 3.12環境の構築
- uv syncの実行（依存関係インストール）
- pre-commitフックのインストール
- Claude Codeの最新版インストール

※ Dev Containerを利用する際は、事前にDockerのインストールが必要です。
