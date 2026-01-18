# 概念データモデル

## 概要

このドキュメントは、mcpax で扱うデータの概要を整理したものである。
厳密な正規化やリレーションシップは後工程で行う。ここでは「こんなデータを使う」という全体像を把握する。

---

## エンティティ一覧

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Config      │     │    Project      │     │ InstalledFile   │
│   (設定情報)     │     │ (管理対象)       │     │ (インストール済) │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ mc_version      │     │ slug            │     │ filename        │
│ loader          │     │ project_type    │     │ hash            │
│ minecraft_dir   │     │ version_pin     │     │ project_slug    │
│ mods_dir        │     │ channel         │     │ installed_at    │
│ shaders_dir     │     └─────────────────┘     └─────────────────┘
│ resourcepacks_dir │
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ ModrinthProject │     │ ModrinthVersion │     │  ModrinthFile   │
│ (API: プロジェクト) │     │ (API: バージョン) │     │  (API: ファイル) │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id              │     │ id              │     │ filename        │
│ slug            │     │ project_id      │     │ url             │
│ title           │     │ version_number  │     │ size            │
│ project_type    │     │ game_versions   │     │ hashes          │
│ description     │     │ loaders         │     │ primary         │
└─────────────────┘     │ version_type    │     └─────────────────┘
                        │ date_published  │
                        │ files           │
                        └─────────────────┘
```

---

## エンティティ詳細

### Config（設定情報）

ツール全体の設定。config.toml から読み込む。

| 項目 | 型 | 説明 |
|------|-----|------|
| mc_version | string | Minecraft バージョン（例: "1.21.4"） |
| loader | string | Mod Loader（例: "fabric"） |
| minecraft_dir | path | Minecraft ディレクトリ（例: ~/.minecraft） |
| mods_dir | path | MOD 配置先（minecraft_dir/mods） |
| shaders_dir | path | Shader 配置先（minecraft_dir/shaderpacks） |
| resourcepacks_dir | path | リソースパック配置先（minecraft_dir/resourcepacks） |

### Project（管理対象）

管理対象のプロジェクト。projects.toml から読み込む。

| 項目 | 型 | 説明 |
|------|-----|------|
| slug | string | Modrinth のプロジェクト識別子（例: "sodium"） |
| project_type | enum | プロジェクト種別: mod / shader / resourcepack |
| version_pin | string? | バージョン固定（省略時は最新） |
| channel | enum? | リリースチャネル: release / beta / alpha（省略時は release） |

### InstalledFile（インストール済みファイル）

ローカルにインストール済みのファイル情報。状態管理用。

| 項目 | 型 | 説明 |
|------|-----|------|
| filename | string | ファイル名 |
| hash | string | SHA-512 ハッシュ |
| project_slug | string | 対応するプロジェクトの slug |
| installed_at | datetime | インストール日時 |

### ModrinthProject（API: プロジェクト情報）

Modrinth API から取得するプロジェクト情報。

| 項目 | 型 | 説明 |
|------|-----|------|
| id | string | プロジェクト ID |
| slug | string | プロジェクト slug |
| title | string | プロジェクト名 |
| project_type | string | 種別: mod / shader / resourcepack |
| description | string | 説明文 |

### ModrinthVersion（API: バージョン情報）

Modrinth API から取得するバージョン情報。

| 項目 | 型 | 説明 |
|------|-----|------|
| id | string | バージョン ID |
| project_id | string | プロジェクト ID |
| version_number | string | バージョン番号（例: "0.6.0"） |
| game_versions | list[string] | 対応 Minecraft バージョン |
| loaders | list[string] | 対応 Loader |
| version_type | string | release / beta / alpha |
| date_published | datetime | 公開日時 |
| files | list[ModrinthFile] | ダウンロード可能なファイル |

### ModrinthFile（API: ファイル情報）

Modrinth API から取得するファイル情報。

| 項目 | 型 | 説明 |
|------|-----|------|
| filename | string | ファイル名 |
| url | string | ダウンロード URL |
| size | int | ファイルサイズ（バイト） |
| hashes | dict | ハッシュ値（sha512, sha1） |
| primary | bool | プライマリファイルかどうか |

---

## データの関係

```
                      ┌──────────────┐
                      │   Config     │
                      └──────────────┘
                             │
                             │ 参照（ディレクトリパス）
                             ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Project    │──────│InstalledFile │──────│  ファイル     │
│  (projects.toml) │ 1:0..1│ (状態管理)   │ 1:1  │ (ローカル)    │
└──────────────┘      └──────────────┘      └──────────────┘
       │
       │ slug で紐付け
       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ModrinthProject│──────│ModrinthVersion│──────│ ModrinthFile │
│  (API)        │ 1:N  │   (API)      │ 1:N  │   (API)      │
└──────────────┘      └──────────────┘      └──────────────┘
```

---

## ファイル形式

### config.toml

```toml
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
# 以下は省略可能（デフォルトは minecraft_dir からの相対パス）
# mods_dir = "~/.minecraft/mods"
# shaders_dir = "~/.minecraft/shaderpacks"
# resourcepacks_dir = "~/.minecraft/resourcepacks"
```

### projects.toml

```toml
[[projects]]
slug = "fabric-api"

[[projects]]
slug = "sodium"

[[projects]]
slug = "iris"

[[projects]]
slug = "complementary-reimagined"
# project_type は API から自動判定

[[projects]]
slug = "some-mod"
version = "1.2.3"  # バージョン固定
channel = "beta"   # beta 版を使用
```

---

## 補足

### 設定ファイルの配置場所

設定ファイル（config.toml, projects.toml）は **カレントディレクトリ** に配置する。
これにより、プロジェクト（Minecraft インスタンス）ごとに異なる設定を持てる。

```
my-minecraft-project/
├── config.toml
├── projects.toml
└── .mcpax-state.json  # インストール状態（自動生成）
```

### プロジェクト種別の判定

プロジェクト種別（mod / shader / resourcepack）は Modrinth API の `project_type` フィールドから取得する。
projects.toml には記載不要（API から自動判定）。

### Loader 指定の扱い

Modrinth API でバージョン一覧を取得する際、`loaders` パラメータはオプション。

- **MOD**: `loaders` パラメータに Loader（例: "fabric"）を指定
- **Shader / Resource Pack**: `loaders` パラメータは省略（Loader に依存しないため）

### インストール状態の管理

インストール済みファイルの情報は別ファイル（例: `.mcpax-state.json`）で管理する案と、
ファイルハッシュを都度計算して Modrinth API のハッシュと比較する案がある。

後者の方がシンプルだが、パフォーマンスに影響する可能性あり。実装時に検討。
