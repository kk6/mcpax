# CRUD マトリックス

## 概要

このドキュメントは、各機能がどのデータに対してどのような操作（CRUD）を行うかを整理する。

---

## CRUD 凡例

| 記号 | 意味 |
|------|------|
| C | Create（作成） |
| R | Read（読み取り） |
| U | Update（更新） |
| D | Delete（削除） |
| - | 操作なし |

---

## コマンド × データ

| コマンド | config.toml | projects.toml | .mcpax-state.json | Modrinth API | ファイル |
|---------|-------------|---------------|-----------------|--------------|---------|
| mcpax init | C | C | - | - | - |
| mcpax add | R | RU | - | R | - |
| mcpax remove | R | RU | RU | - | D |
| mcpax list | R | R | R | - | - |
| mcpax search | R | - | - | R | - |
| mcpax update | R | R | RU | R | CUD |
| mcpax install | R | R | CU | R | C |

---

## 機能 × データ

### 設定管理機能

| 機能 | config.toml | projects.toml | .mcpax-state.json |
|-----|-------------|---------------|-----------------|
| F-101 設定ファイル生成 | C | - | - |
| F-102 設定ファイル読み込み | R | - | - |
| F-103 プロジェクトリスト生成 | - | C | - |
| F-104 プロジェクトリスト読み込み | - | R | - |
| F-105 プロジェクトリスト書き込み | - | U | - |
| F-106 パス解決 | - | - | - |
| F-107 設定バリデーション | R | - | - |

### Modrinth API 連携機能

| 機能 | Modrinth API |
|-----|--------------|
| F-201 プロジェクト情報取得 | R |
| F-202 プロジェクト検索 | R |
| F-203 バージョン一覧取得 | R |
| F-204 対応バージョン抽出 | - |
| F-205 レートリミット制御 | - |
| F-206 リトライ処理 | - |

### ダウンロード機能

| 機能 | ファイル（mods 等） |
|-----|-------------------|
| F-301 ファイルダウンロード | C |
| F-302 並列ダウンロード | C |
| F-303 ハッシュ検証 | R |
| F-304 進捗表示 | - |

### ファイル管理機能

| 機能 | .mcpax-state.json | ファイル（mods 等） | バックアップ |
|-----|-----------------|-------------------|-------------|
| F-401 ディレクトリ判定 | - | - | - |
| F-402 ファイル配置 | U | C | - |
| F-403 ファイルバックアップ | - | R | C |
| F-404 ファイル削除 | U | D | - |
| F-405 インストール状態確認 | R | R | - |
| F-406 インストールファイル特定 | R | - | - |

### 更新管理機能

| 機能 | .mcpax-state.json | Modrinth API |
|-----|-----------------|--------------|
| F-501 更新確認 | R | R |
| F-502 バージョン比較 | R | - |
| F-503 更新適用 | U | - |

---

## データライフサイクル

### config.toml

```
┌─────────┐     ┌─────────┐
│ 未作成  │────►│  存在   │
└─────────┘     └────┬────┘
   mcpax init          │
                     │ 手動編集
                     ▼
                ┌─────────┐
                │  更新   │
                └─────────┘
```

- 作成: `mcpax init`
- 読み取り: 全コマンド（init 以外）
- 更新: 手動編集のみ（ツールからは更新しない）
- 削除: 手動削除のみ

### projects.toml

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│ 未作成  │────►│  存在   │◄───►│ 更新中  │
└─────────┘     └────┬────┘     └─────────┘
   mcpax init          │              ▲
                     │              │
                     └──────────────┘
                        mcpax add / remove
```

- 作成: `mcpax init`
- 読み取り: 全コマンド（init 以外）
- 更新: `mcpax add`, `mcpax remove`
- 削除: 手動削除のみ

### .mcpax-state.json

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│ 未作成  │────►│  存在   │◄───►│ 更新中  │
└─────────┘     └────┬────┘     └─────────┘
  初回 install       │              ▲
                     │              │
                     └──────────────┘
                     install / update / remove
```

- 作成: 初回 `mcpax install` 時に自動作成
- 読み取り: `mcpax list`, `mcpax update`, `mcpax install`
- 更新: `mcpax install`, `mcpax update`, `mcpax remove`
- 削除: 手動削除のみ

### インストールファイル（MOD / Shader / Resource Pack）

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐
│ 未作成  │────►│ インストール │────►│   更新済み   │
└─────────┘     └──────┬──────┘     └──────┬──────┘
   install            │                    │
                      ▼                    │
               ┌─────────────┐             │
               │  バックアップ │◄───────────┘
               └──────┬──────┘    update
                      │
                      ▼
               ┌─────────────┐
               │    削除     │
               └─────────────┘
                   remove
```

- 作成: `mcpax install`
- 読み取: ハッシュ検証時
- 更新: `mcpax update`（古いファイル → バックアップ → 新しいファイル）
- 削除: `mcpax remove --delete-file`

---

## トランザクション境界

### mcpax install

```
1. config.toml 読み込み (R)
2. projects.toml 読み込み (R)
3. Modrinth API 問い合わせ (R)
4. ファイルダウンロード (C) ← 失敗時はロールバック
5. ハッシュ検証 (R) ← 失敗時はファイル削除
6. ファイル配置 (C)
7. .mcpax-state.json 更新 (CU) ← 成功時のみ
```

### mcpax update

```
1. config.toml 読み込み (R)
2. projects.toml 読み込み (R)
3. .mcpax-state.json 読み込み (R)
4. Modrinth API 問い合わせ (R)
5. 更新対象の特定
6. for each 更新対象:
   a. ファイルダウンロード (C) ← 失敗時はスキップ
   b. ハッシュ検証 (R) ← 失敗時はファイル削除・スキップ
   c. 古いファイルバックアップ (R→C)
   d. 新しいファイル配置 (C)
   e. .mcpax-state.json 更新 (U)
7. 結果レポート
```

### mcpax remove

```
1. config.toml 読み込み (R)
2. projects.toml 読み込み (R)
3. .mcpax-state.json 読み込み (R)
4. projects.toml から削除 (U)
5. if --delete-file:
   a. ファイル削除 (D)
   b. .mcpax-state.json から削除 (U)
```

---

## 整合性ルール

### projects.toml と .mcpax-state.json

- `projects.toml` に存在するが `.mcpax-state.json` にない → 未インストール
- `projects.toml` に存在し `.mcpax-state.json` にもある → インストール済み
- `projects.toml` にないが `.mcpax-state.json` にある → 孤立（警告を出す）

### .mcpax-state.json とファイルシステム

- `.mcpax-state.json` に記録があるがファイルが存在しない → 不整合（エラー）
- ファイルが存在するが `.mcpax-state.json` に記録がない → mcpax 管理外

### ハッシュ整合性

- インストール済みファイルのハッシュと `.mcpax-state.json` のハッシュが一致しない → 改竄または破損
