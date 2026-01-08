# mcpax

Minecraft の MOD/シェーダー/リソースパックを Modrinth API 経由で管理する CLI ツール。

## プロジェクト概要

### 解決する課題
約30個の Minecraft プロジェクトを複数バージョンで管理する際の手動更新作業を自動化する。

### 主な機能
- TOML 形式の設定ファイルで管理対象プロジェクトを定義
- Modrinth API で互換バージョンを自動取得
- SHA512 ハッシュ検証による安全なダウンロード
- プロジェクト種別（mod/shader/resourcepack）に応じた自動配置

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| 言語 | Python 3.13+ |
| パッケージ管理 | uv |
| 型チェック | ty |
| リンター/フォーマッター | ruff |
| テスト | pytest, pytest-asyncio, pytest-httpx |
| HTTP クライアント | httpx |
| CLI | typer |
| 出力装飾 | rich |
| TUI（将来） | textual |

## 開発方針

### TDD（t-wada式）
1. **Red**: 失敗するテストを書く
2. **Green**: テストを通す最小限のコードを書く
3. **Refactor**: リファクタリング

テストを先に書くこと。実装コードを書く前に必ずテストが存在すること。

### コード品質
- 全ての関数・メソッドに型ヒントを付与
- `ty check src` がエラーなしで通ること
- `ruff check src` がエラーなしで通ること
- `ruff format src` でフォーマット済みであること

### コミット前チェック
```bash
uv run ruff format src tests
uv run ruff check src tests --fix
uv run ty check src
uv run pytest
```

## アーキテクチャ

```
src/mcpax/
├── __init__.py
├── core/                # ビジネスロジック層
│   ├── __init__.py
│   ├── models.py        # Pydantic データモデル
│   ├── config.py        # 設定ファイル読み書き
│   ├── api.py           # Modrinth API クライアント
│   ├── downloader.py    # ダウンロード・ハッシュ検証
│   └── manager.py       # プロジェクト管理のオーケストレーション
├── cli/                 # CLI インターフェース
│   ├── __init__.py
│   └── app.py           # typer アプリケーション
└── tui/                 # TUI インターフェース（将来）
    └── __init__.py
```

### 設計原則
- **Unix哲学**: 各コマンドは1つのことをうまくやる
- **依存性の方向**: CLI/TUI → core（逆方向の依存禁止）
- **テスト容易性**: 外部依存（API、ファイルシステム）は注入可能に

## 設定ファイル

### config.toml
```toml
[minecraft]
version = "1.21.4"
loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
```

### projects.toml
```toml
[[projects]]
slug = "fabric-api"

[[projects]]
slug = "sodium"

[[projects]]
slug = "complementary-unbound"  # シェーダー
```

## CLI コマンド体系

```bash
mcpax init                    # 設定ファイル初期化
mcpax add <slug>              # プロジェクト追加
mcpax remove <slug>           # プロジェクト削除
mcpax list                    # 登録プロジェクト一覧
mcpax search <query>          # Modrinth 検索（別コマンド）
mcpax install [--all]         # インストール
mcpax update [--check]        # 更新確認・適用
mcpax status                  # インストール状態表示
```

## テスト方針

### ディレクトリ構造
```
tests/
├── conftest.py             # 共通フィクスチャ
├── unit/                   # ユニットテスト
│   ├── test_models.py
│   ├── test_config.py
│   └── test_api.py
├── integration/            # 統合テスト
│   └── test_manager.py
└── fixtures/               # テストデータ
    ├── config.toml
    └── projects.toml
```

### モック方針
- Modrinth API: `pytest-httpx` でモック
- ファイルシステム: `tmp_path` フィクスチャを使用
- 実際の API を叩くテストは `@pytest.mark.integration` でマーク

## 実装優先順位

### Phase 1: Core（現在）
1. models.py - データモデル定義
2. config.py - 設定ファイル読み書き
3. api.py - Modrinth API クライアント
4. downloader.py - ダウンロード処理
5. manager.py - オーケストレーション

### Phase 2: CLI
6. cli/app.py - typer コマンド実装

### Phase 3: TUI（将来）
7. tui/ - textual による TUI

## 注意事項

### Modrinth API
- ベース URL: `https://api.modrinth.com/v2`
- レートリミット: 300 req/min
- User-Agent ヘッダー必須（プロジェクト名/バージョン形式）

### プロジェクト種別の判定
API レスポンスの `project_type` フィールドで判定：
- `mod` → `mods/` ディレクトリ
- `shader` → `shaderpacks/` ディレクトリ
- `resourcepack` → `resourcepacks/` ディレクトリ

### ファイル名の扱い
- ダウンロードファイル名は API レスポンスの `filename` を使用
- slug とファイル名は一致しないことがある
