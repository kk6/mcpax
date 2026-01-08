# mcpax

Minecraft の MOD / Shader / Resource Pack を Modrinth API 経由で管理する CLI ツール。

## 特徴

- TOML 形式の設定ファイルでプロジェクトリストを管理
- 指定した Minecraft バージョン・Loader に対応するプロジェクトを自動取得
- プロジェクト種別（MOD / Shader / Resource Pack）に応じた適切なディレクトリ配置
- ハッシュ検証による安全なダウンロード
- 差分更新（変更があったプロジェクトのみダウンロード）

## 必要環境

- Python 3.13+
- Minecraft（Fabric Loader）

## インストール

```bash
# 開発版
git clone https://github.com/kk6/mcpax.git
cd mcpax
uv sync
```

## 使い方

### 1. 初期セットアップ

```bash
mcpax init
```

### 2. 設定ファイルの作成

`config.toml`:

```toml
[minecraft]
version = "1.21.4"
loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
```

`projects.toml`:

```toml
[[projects]]
slug = "fabric-api"

[[projects]]
slug = "sodium"

[[projects]]
slug = "complementary-reimagined"
```

### 3. プロジェクトの追加

```bash
# slug がわかっている場合
mcpax add sodium

# slug がわからない場合は検索
mcpax search shader
```

### 4. プロジェクトのインストール

```bash
# 全プロジェクトをインストール
mcpax install --all

# 特定のプロジェクトをインストール
mcpax install sodium
```

### 5. 更新確認・適用

```bash
# 更新を確認
mcpax update --check

# 更新を適用
mcpax update
```

### 6. 一覧確認

```bash
mcpax list
```

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

## ドキュメント

### 要件定義（「はじめよう！要件定義」準拠）

- [企画書](docs/01_project_charter.md)
- [全体像](docs/02_system_overview.md)
- [実現したいこと一覧](docs/03_requirements_list.md)
- [行動シナリオ](docs/04_user_scenarios.md)
- [概念データモデル](docs/05_conceptual_data_model.md)

### 技術ドキュメント

- [要件定義書](docs/requirements.md)
- [アーキテクチャ設計書](docs/architecture.md)
- [Modrinth API 仕様メモ](docs/modrinth-api.md)
- [開発ロードマップ](docs/roadmap.md)

## ライセンス

MIT
