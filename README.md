# mcpax

Minecraft の MOD / Modpack / Shader / Resource Pack を Modrinth API 経由で管理する CLI ツール。

## 特徴

- TOML 形式の設定ファイルでプロジェクトリストを管理
- 指定した Minecraft バージョン・Loader に対応するプロジェクトを自動取得
- プロジェクト種別（MOD / Shader / Resource Pack）に応じた適切なディレクトリ配置
- バージョンピニング（特定バージョンで固定可能）
- リリースチャンネル指定（release / beta / alpha）
- Modpack の検索機能（インストールは未対応）
- ハッシュ検証による安全なダウンロード
- 差分更新（変更があったプロジェクトのみダウンロード）

## 必要環境

- Python 3.13+
- Minecraft（Fabric Loader）
- TUI 利用時: `textual`（optional dependency）

## インストール

```bash
# 開発版
git clone https://github.com/kk6/mcpax.git
cd mcpax
uv sync

# TUI を使う場合
uv pip install -e ".[tui]"
```

## 使い方

### バージョン確認

```bash
mcpax --version
mcpax -V
```

### 1. 初期セットアップ

```bash
# 対話形式で初期化（Minecraft バージョン、Mod Loader 等を聞かれる）
mcpax init

# デフォルト値で非対話的に初期化
mcpax init --non-interactive
mcpax init -y

# 既存の設定ファイルを上書きして再初期化
mcpax init --force
mcpax init -f
```

このコマンドで `config.toml` と `projects.toml` が自動生成されます。

#### 設定ファイルの場所

設定ファイルは [XDG Base Directory 仕様](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) に準拠した場所に配置されます：

- **XDG_CONFIG_HOME が設定されている場合**: `$XDG_CONFIG_HOME/mcpax/`
- **未設定の場合（デフォルト）**: `~/.config/mcpax/`

```bash
# デフォルトの配置場所
~/.config/mcpax/config.toml
~/.config/mcpax/projects.toml
```

### 2. 設定の管理

CLI から設定値の確認・変更ができます。

```bash
# 設定ファイルのパスを表示
mcpax config path

# 設定値を取得
mcpax config get minecraft.version
mcpax config get download.max_concurrent

# 設定値を変更
mcpax config set minecraft.version 1.21.5
mcpax config set download.max_concurrent 10
mcpax config set download.verify_hash true

# 全設定を一覧表示
mcpax config list
mcpax config list --json
```

#### 設定ファイルの直接編集

`config.toml` を直接編集することも可能です。

`config.toml`:

```toml
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
```

`projects.toml`:

```toml
[[projects]]
slug = "fabric-api"
project_type = "mod"

[[projects]]
slug = "sodium"
project_type = "mod"

# バージョン固定（特定バージョンで維持したい場合）
[[projects]]
slug = "iris"
project_type = "mod"
version = "1.7.0"

[[projects]]
slug = "complementary-reimagined"
project_type = "shader"
```

### 3. プロジェクトの追加

```bash
# slug がわかっている場合
mcpax add sodium

# 特定バージョンで固定したい場合
mcpax add iris --version 1.7.0

# リリースチャンネルを指定（release/beta/alpha）
mcpax add iris --channel beta
mcpax add iris -c beta

# slug がわからない場合は検索
mcpax search shader
mcpax search sodium --type mod --limit 5
mcpax search "optimization pack" --type modpack
mcpax search iris --json
```

### 4. プロジェクトの削除

```bash
# プロジェクトを管理リストから削除（確認プロンプトあり）
mcpax remove sodium

# 確認プロンプトをスキップ
mcpax remove sodium --yes
mcpax remove sodium -y

# インストール済みファイルも同時に削除
mcpax remove sodium --delete-file
mcpax remove sodium -d

# オプションの組み合わせ
mcpax remove sodium -d -y
```

### 5. プロジェクトのインストール

```bash
# 全プロジェクトをインストール
mcpax install --all

# 特定のプロジェクトをインストール
mcpax install sodium
```

### 6. 更新確認・適用

```bash
# 更新を確認（ダウンロードしない）
mcpax update --check
mcpax update -c

# 更新を適用（確認プロンプトあり）
mcpax update

# 更新を適用（確認プロンプトをスキップ）
mcpax update --yes
mcpax update -y
```

### 7. 一覧確認

```bash
mcpax list
mcpax list --type mod
mcpax list --type shader
mcpax list --status installed
mcpax list --status not-installed
mcpax list --status outdated
mcpax list --json
mcpax list --no-update          # 更新チェックをスキップ（高速表示）
mcpax list --no-cache           # APIキャッシュをバイパス
mcpax list --max-concurrency 5  # API並列リクエスト数を制限
```

### 8. TUI（Terminal UI）

TUI は optional dependency です。利用する場合は `textual` を追加インストールしてください。

```bash
uv pip install -e ".[tui]"
```

起動:

```bash
mcpax tui
```

主な操作:

- `q`: 終了
- `r`: 更新チェック
- `i`: 全プロジェクトのインストール/更新
- `s`: 設定画面
- `Enter`: 詳細表示
- 検索: 検索欄で Enter → 検索結果画面（`a` で追加 / `Esc` で戻る）

## CLI コマンドリファレンス

| コマンド | 説明 |
|---------|------|
| `mcpax --version, -V` | バージョン表示 |
| `mcpax init` | 設定ファイルの初期化（`-y`: 非対話、`-f`: 上書き） |
| `mcpax add <slug>` | プロジェクトを管理リストに追加（`-v`: バージョン固定、`-c`: チャンネル指定） |
| `mcpax remove <slug>` | プロジェクトを管理リストから削除（`-y`: 確認スキップ、`-d`: ファイル削除） |
| `mcpax install [slug] \| --all` | プロジェクトのインストール |
| `mcpax list` | 管理プロジェクトの一覧表示（`-t`: タイプ、`-s`: ステータス、`--json`） |
| `mcpax search <query>` | Modrinth でプロジェクトを検索（`-t`: タイプ、`-l`: 件数、`--json`） |
| `mcpax update` | 更新の確認・適用（`-c`: 確認のみ、`-y`: 確認スキップ） |
| `mcpax config path` | 設定ファイルのパス表示 |
| `mcpax config get <key>` | 設定値の取得 |
| `mcpax config set <key> <value>` | 設定値の変更 |
| `mcpax config list` | 全設定の一覧表示（`--json`） |
| `mcpax tui` | TUI インターフェースの起動 |

## 開発

```bash
# 依存関係のインストール
uv sync

# テスト実行
pytest

# 型チェック
ty check src

# リント
ruff check src
```

## 開発状況

### Phase 1: Core 実装 ✅

| モジュール | 状態 | テスト |
|-----------|------|--------|
| models.py | ✅ 完了 | 44 テスト |
| config.py | ✅ 完了 | 101 テスト |
| api.py | ✅ 完了 | 55 テスト |
| downloader.py | ✅ 完了 | 28 テスト |
| manager.py | ✅ 完了 | 60 テスト |
| cache.py | ✅ 完了 | 12 テスト |
| exceptions.py | ✅ 完了 | 12 テスト |

**完了した機能**:
- F-101～F-107（設定管理機能 7件）
- F-201〜F-206（API クライアント機能 6件）
- F-301～F-304（ダウンロード機能 4件）
- F-401～F-406（ファイル管理機能 6件）
- F-501～F-503（更新管理機能 3件）

### Phase 2: CLI 実装 ✅

| コマンド | 状態 | テスト |
|---------|------|--------|
| init | ✅ 完了 | テスト有 |
| add | ✅ 完了 | テスト有 |
| remove | ✅ 完了 | テスト有 |
| install | ✅ 完了 | テスト有 |
| list | ✅ 完了 | テスト有 |
| search | ✅ 完了 | テスト有 |
| update | ✅ 完了 | テスト有 |
| config (path/get/set/list) | ✅ 完了 | テスト有 |
| tui | ✅ 完了 | テスト有 |

### Phase 3: TUI 実装 🧪

`mcpax tui` で利用可能（`textual` の optional dependency が必要）。

## ドキュメント

### 要件定義（「はじめよう！要件定義」準拠）

- [企画書](docs/01_project_charter.md)
- [全体像](docs/02_system_overview.md)
- [実現したいこと一覧](docs/03_requirements_list.md)
- [行動シナリオ](docs/04_user_scenarios.md)
- [概念データモデル](docs/05_conceptual_data_model.md)
- [UI 定義](docs/06_ui_definition.md)
- [機能定義](docs/07_function_definition.md)
- [データ定義](docs/08_data_definition.md)
- [CRUD マトリックス](docs/09_crud_matrix.md)
- [一覧](docs/10_summary.md)
- [アーキテクチャ設計書](docs/11_architecture.md)

### 技術ドキュメント

- [Modrinth API 仕様メモ](docs/modrinth-api.md)
- [Claude Code スキル](docs/claude-skills.md)

## ライセンス

MIT
