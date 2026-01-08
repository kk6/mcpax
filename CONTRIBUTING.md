# コントリビューションガイド

mcpax プロジェクトへの貢献方法について説明します。

## 開発フロー概要

チケット駆動開発を採用しています。すべての変更は GitHub Issue を起点として行います。

```
┌─────────────────────────────────────────────────────────────────┐
│                      開発サイクル                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Issue 作成    2. ブランチ作成    3. 実装・テスト            │
│  ┌──────────┐    ┌──────────────┐   ┌──────────────┐           │
│  │  Issue   │───▶│   Branch     │──▶│  Commit(s)   │           │
│  │  #123    │    │ feat/123-... │   │  TDD で実装  │           │
│  └──────────┘    └──────────────┘   └──────┬───────┘           │
│                                            │                    │
│  6. マージ        5. レビュー        4. PR 作成                 │
│  ┌──────────┐    ┌──────────────┐   ┌──────┴───────┐           │
│  │  Merge   │◀───│   Review     │◀──│  Pull        │           │
│  │ + Close  │    │   Approve    │   │  Request     │           │
│  └──────────┘    └──────────────┘   └──────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 1. Issue の作成

### Issue テンプレート

目的に応じて適切なテンプレートを選択してください：

| テンプレート | 用途 |
|-------------|------|
| Bug Report | バグの報告 |
| Feature Request | 新機能の提案 |
| Task | 実装タスクの作成 |

### ラベル体系

| ラベル | 説明 |
|--------|------|
| `bug` | バグ修正 |
| `enhancement` | 機能追加・改善 |
| `task` | 実装タスク |
| `documentation` | ドキュメント更新 |
| `refactor` | リファクタリング |
| `test` | テスト追加・修正 |
| `priority: high` | 優先度：高 |
| `priority: medium` | 優先度：中 |
| `priority: low` | 優先度：低 |

### Issue タイトルの規約

```
[種別] 簡潔な説明

例：
[Bug] mcpax status コマンドがエラーを返す
[Feature] 検索コマンドの追加
[Task] models.py の実装
```

## 2. ブランチ戦略

### ブランチ命名規則

```
<type>/<issue-number>-<short-description>
```

| type | 用途 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメント |
| `refactor` | リファクタリング |
| `test` | テスト |
| `chore` | その他（CI、設定等） |

**例：**

```bash
git checkout -b feat/123-add-search-command
git checkout -b fix/456-status-error
git checkout -b docs/789-update-readme
```

### ブランチ作成手順

```bash
# main ブランチを最新に更新
git checkout main
git pull origin main

# 新しいブランチを作成
git checkout -b feat/123-add-search-command
```

## 3. コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/) に従います。

### 形式

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### type 一覧

| type | 説明 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみの変更 |
| `style` | コードの意味に影響しない変更（空白、フォーマット等） |
| `refactor` | バグ修正でも機能追加でもないコード変更 |
| `test` | テストの追加・修正 |
| `chore` | ビルドプロセスやツールの変更 |

### scope（任意）

変更対象のモジュールを指定：

- `core` - ビジネスロジック
- `cli` - CLI インターフェース
- `api` - Modrinth API クライアント
- `config` - 設定関連

### Issue との紐付け

コミットメッセージのフッターに Issue 番号を記載：

```
feat(api): Modrinth API クライアントを実装

- プロジェクト検索エンドポイントを追加
- バージョン取得エンドポイントを追加

Refs #123
```

### 例

```bash
# 機能追加
git commit -m "feat(cli): 検索コマンドを追加

Modrinth からプロジェクトを検索する機能を追加

Refs #123"

# バグ修正
git commit -m "fix(core): ハッシュ検証のエラーを修正

SHA512 ハッシュの比較で大文字小文字を区別していた問題を修正

Fixes #456"

# テスト追加
git commit -m "test(api): API クライアントのユニットテストを追加

Refs #123"
```

## 4. TDD（テスト駆動開発）

t-wada 式の TDD を採用しています。

### Red-Green-Refactor サイクル

1. **Red**: 失敗するテストを書く
2. **Green**: テストを通す最小限のコードを書く
3. **Refactor**: リファクタリング

### 実装前チェック

コードを書く前に、必ずテストが存在することを確認してください。

```bash
# テスト実行
uv run pytest

# 特定のテストファイルを実行
uv run pytest tests/unit/test_api.py
```

## 5. コードの品質基準

### 必須チェック

コミット前に以下を実行してください：

```bash
# フォーマット
uv run ruff format src tests

# リント
uv run ruff check src tests --fix

# 型チェック
uv run ty check src

# テスト
uv run pytest
```

### Pre-commit フック

上記は pre-commit フックで自動実行されます：

```bash
# フックのインストール
uv run pre-commit install
```

## 6. Pull Request の作成

### PR タイトル

コミットメッセージと同じ形式を使用：

```
feat(api): Modrinth API クライアントを実装
```

### PR テンプレート

PR 作成時に自動的にテンプレートが表示されます。以下を記載してください：

- 変更の概要
- 関連 Issue（`Closes #123` で自動クローズ）
- 変更種別
- チェックリストの確認

### Issue との紐付け

PR 本文に以下のキーワードを使用すると、マージ時に Issue が自動クローズされます：

- `Closes #123`
- `Fixes #123`
- `Resolves #123`

## 7. コードレビュー

### レビュー観点

- 機能要件を満たしているか
- テストが十分か
- コード品質（可読性、保守性）
- セキュリティ上の問題がないか
- パフォーマンスへの影響

### 承認条件

- CI が全てパス
- 最低 1 人のレビュアーによる承認
- コンフリクトがない

## 8. マージ

### マージ方法

**Squash and merge** を推奨します。複数のコミットが 1 つにまとまり、履歴がクリーンになります。

### マージ後

- Issue が自動クローズされます（`Closes #123` を使用した場合）
- ローカルブランチを削除してください

```bash
git checkout main
git pull origin main
git branch -d feat/123-add-search-command
```

## クイックリファレンス

### ブランチ作成から PR までの流れ

```bash
# 1. main を最新に
git checkout main && git pull

# 2. ブランチ作成
git checkout -b feat/123-description

# 3. テストを書く（Red）
# 4. 実装する（Green）
# 5. リファクタリング（Refactor）

# 6. コミット
git add .
git commit -m "feat(scope): description

Refs #123"

# 7. プッシュ
git push -u origin feat/123-description

# 8. GitHub で PR 作成
```

### よく使うコマンド

```bash
# 品質チェック一式
uv run ruff format src tests && uv run ruff check src tests --fix && uv run ty check src && uv run pytest

# テスト実行（カバレッジ付き）
uv run pytest --cov=src

# 特定のテストのみ実行
uv run pytest -k "test_api"
```
