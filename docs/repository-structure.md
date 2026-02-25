# リポジトリ構造定義書 (Repository Structure Document)

## プロジェクト構造

```
claude-ai-app/                    # プロジェクトルート
├── src/                          # ソースコード
│   └── app/                      # アプリケーションパッケージ
│       ├── __init__.py
│       ├── main.py               # FastAPIアプリ・エントリーポイント
│       ├── routers/              # APIレイヤー（FastAPI Router）
│       │   └── debate.py         # 議論セッション関連エンドポイント
│       ├── services/             # サービスレイヤー（ビジネスロジック）
│       │   ├── debate_orchestrator.py # DebateOrchestrator（議論制御）
│       │   └── agent_runner.py        # AgentRunner（1エージェント実行）
│       ├── infra/                # インフラレイヤー（外部依存）
│       │   ├── web_search.py     # Tavily Web検索ツール
│       │   └── session_store.py  # セッション管理
│       ├── models/               # データモデル定義（dataclass）
│       │   └── debate.py         # Persona, DebateSession等の型定義
│       └── static/               # フロントエンド静的ファイル
│           └── index.html        # 設定画面・議論画面・CSS・JS（単一ファイルSPA）
├── tests/                        # テストコード
│   ├── unit/                     # ユニットテスト
│   │   ├── services/
│   │   │   ├── test_debate_orchestrator.py
│   │   │   └── test_agent_runner.py
│   │   └── infra/
│   │       └── test_web_search.py
│   └── integration/              # 統合テスト
│       └── test_debate_api.py
├── docs/                         # プロジェクトドキュメント
│   ├── ideas/                    # アイデア・壁打ちメモ
│   ├── product-requirements.md   # PRD
│   ├── functional-design.md      # 機能設計書
│   ├── architecture.md           # アーキテクチャ設計書
│   ├── repository-structure.md   # 本ドキュメント
│   ├── development-guidelines.md # 開発ガイドライン
│   └── glossary.md               # 用語集
├── .steering/                    # 作業単位のステアリングファイル
├── .claude/                      # Claude Code設定
│   ├── commands/                 # スラッシュコマンド定義
│   ├── skills/                   # スキル定義
│   └── agents/                   # サブエージェント定義
├── .env.example                  # 環境変数テンプレート（Gitに含める）
├── .env                          # 実際の認証情報（Gitに含めない）
├── pyproject.toml                # プロジェクト設定・依存関係管理
├── uv.lock                       # 依存関係ロックファイル
├── CLAUDE.md                     # Claude Code向けプロジェクトメモリ
└── README.md                     # プロジェクト概要
```

---

## ディレクトリ詳細

### src/app/ （アプリケーションパッケージ）

#### routers/ - APIレイヤー

**役割**: HTTPリクエストの受付・バリデーション・SSEストリームの管理

**配置ファイル**:
- `debate.py`: 議論セッションの開始（POST）とSSEストリーム（GET）エンドポイント

**命名規則**:
- ファイル名: リソース名の単数形 snake_case（例: `debate.py`）
- ルーター変数: `router = APIRouter(prefix="/api/debate")`

**依存関係**:
- 依存可能: `services/`
- 依存禁止: `infra/`（直接呼び出し不可）

```
routers/
└── debate.py        # POST /api/debate/start, GET /api/debate/{id}/stream
```

---

#### services/ - サービスレイヤー

**役割**: ビジネスロジックの実装（議論制御・エージェント実行）

**配置ファイル**:
- `debate_orchestrator.py`: `DebateOrchestrator` クラス（ターン管理・まとめ生成）
- `agent_runner.py`: `AgentRunner` クラス（tool_useループ・1ターン発言生成）

**命名規則**:
- ファイル名: 役割を表す snake_case + `_runner` / `_orchestrator` 等
- クラス名: PascalCase（例: `DebateOrchestrator`, `AgentRunner`）

**依存関係**:
- 依存可能: `infra/`, `models/`
- 依存禁止: `routers/`

```
services/
├── debate_orchestrator.py  # DebateOrchestrator: 議論全体の制御
└── agent_runner.py         # AgentRunner: 1エージェントの発言生成
```

---

#### infra/ - インフラレイヤー

**役割**: 外部サービスとの通信（AWS Bedrock, Tavily）

**配置ファイル**:
- `web_search.py`: `WebSearchTool` クラス（Tavily APIのラッパー）
- `session_store.py`: `SessionStore` クラス（セッション管理）

**命名規則**:
- ファイル名: 外部サービス名または役割 snake_case（例: `web_search.py`）

**依存関係**:
- 依存可能: `models/`、外部ライブラリ（anthropic, tavily-python）
- 依存禁止: `services/`, `routers/`

```
infra/
├── web_search.py     # Tavily APIでWeb検索する
└── session_store.py  # セッションデータをメモリ管理する
```

---

#### models/ - データモデル定義

**役割**: アプリケーション全体で使用する型定義（dataclass / Pydantic）

**配置ファイル**:
- `debate.py`: `Persona`, `DebateConfig`, `DebateTurn`, `DebateSession`, `ToolCall` 等

**命名規則**:
- ファイル名: ドメイン名 snake_case（例: `debate.py`）
- クラス名: PascalCase

**依存関係**:
- 依存可能: Pythonの標準ライブラリのみ
- 依存禁止: `services/`, `infra/`, `routers/`（最下位レイヤー）

```
models/
└── debate.py  # Persona, DebateConfig, DebateTurn, DebateSession, ToolCall
```

---

#### static/ - フロントエンド静的ファイル

**役割**: HTML/CSS/JSによるフロントエンド一式

**配置ファイル**:
- `index.html`: HTML・CSS・JS をすべて含む単一ファイルSPA（設定画面 + 議論画面）

**配信方法**: FastAPIの `StaticFiles` で `/` にマウント

```
static/
└── index.html   # SPA（設定画面 + 議論画面 + スタイル + ロジックを1ファイルで管理）
```

---

### tests/ - テストコード

#### unit/ - ユニットテスト

**役割**: クラス・関数単体の動作確認（外部API呼び出しはモック）

**構造**:
```
tests/unit/
├── services/
│   ├── test_debate_orchestrator.py  # DebateOrchestratorのターン管理ロジック
│   └── test_agent_runner.py         # AgentRunnerのtool_useループ
└── infra/
    └── test_web_search.py           # WebSearchToolの正常系・エラー系
```

**命名規則**: `test_[対象ファイル名].py`

---

#### integration/ - 統合テスト

**役割**: FastAPIエンドポイントの動作確認（モックLLM使用）

**構造**:
```
tests/integration/
└── test_debate_api.py   # /api/debate/start の正常系・バリデーションエラー系
```

---

## ファイル配置規則

### ソースファイル

| ファイル種別 | 配置先 | 命名規則 | 例 |
|------------|--------|---------|-----|
| FastAPI Router | `src/app/routers/` | `[リソース名].py` | `debate.py` |
| サービスクラス | `src/app/services/` | `[役割]_[種別].py` | `debate_orchestrator.py` |
| インフラクラス | `src/app/infra/` | `[外部サービス名].py` | `web_search.py` |
| データモデル | `src/app/models/` | `[ドメイン名].py` | `debate.py` |
| 静的ファイル | `src/app/static/` | 自由（Web標準に従う） | `index.html` |

### テストファイル

| テスト種別 | 配置先 | 命名規則 | 例 |
|-----------|--------|---------|-----|
| ユニットテスト | `tests/unit/[layer]/` | `test_[対象].py` | `test_debate_orchestrator.py` |
| 統合テスト | `tests/integration/` | `test_[機能].py` | `test_debate_api.py` |

### 環境変数ファイル

| ファイル | Git管理 | 用途 |
|---------|---------|------|
| `.env.example` | ✅ 含める | 必要な環境変数の一覧（値は空） |
| `.env` | ❌ 含めない | 実際の認証情報 |

**.env.example の内容**:
```bash
# AWS Bedrock
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1

# Tavily Web Search
TAVILY_API_KEY=
```

---

## 命名規則まとめ

### ディレクトリ名
- レイヤーディレクトリ: **複数形 + snake_case**（`routers/`, `services/`, `infra/`, `models/`）

### Pythonファイル名
- 全て **snake_case**（例: `debate.py`, `agent_runner.py`）

### クラス名
- 全て **PascalCase**（例: `DebateOrchestrator`, `AgentRunner`, `WebSearchTool`）

### 関数・変数名
- 全て **snake_case**（例: `run_debate()`, `session_id`）

---

## 依存関係のルール

```
routers/（APIレイヤー）
    ↓ 依存OK
services/（サービスレイヤー）
    ↓ 依存OK
infra/ + models/（インフラ・モデルレイヤー）
```

**禁止される依存方向**:
- `models/` → `services/` / `infra/` / `routers/` ❌
- `infra/` → `services/` / `routers/` ❌
- `services/` → `routers/` ❌

---

## 除外設定

### .gitignore に追加すべきもの

```gitignore
# Python
.venv/
__pycache__/
*.pyc
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
.coverage

# 環境変数（認証情報）
.env

# OS
.DS_Store

# ログ
*.log
```

### pyproject.toml のツール除外設定

```toml
[tool.ruff]
exclude = [".venv", ".steering", "htmlcov"]

[tool.mypy]
exclude = [".venv", ".steering"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```
