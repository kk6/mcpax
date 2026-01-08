# UI 定義（CLI）

## 概要

このドキュメントは、mcpax の CLI インターフェースを定義する。
行動シナリオ（04_user_scenarios.md）を元に、利用者が実行するコマンドを整理した。

---

## コマンド一覧

| コマンド | 説明 | 対応シナリオ |
|---------|------|-------------|
| `mcpax init` | 初期セットアップ | S-005 |
| `mcpax add <slug>` | プロジェクトを追加 | S-002 |
| `mcpax remove <slug>` | プロジェクトを削除 | S-003 |
| `mcpax list` | 管理対象の一覧表示 | S-004 |
| `mcpax search <query>` | プロジェクトを検索 | S-006 |
| `mcpax update` | 更新を確認して適用 | S-001 |
| `mcpax install` | プロジェクトをインストール | S-001 |

---

## コマンド詳細

### mcpax init

初期設定ファイルを作成する。

```
mcpax init
```

#### 動作

1. 対話的に設定を収集
   - Minecraft バージョン（デフォルト: 最新安定版）
   - Loader（デフォルト: fabric）
   - Minecraft ディレクトリ（デフォルト: ~/.minecraft）
2. `config.toml` を生成
3. 空の `projects.toml` を生成

#### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--non-interactive` | `-y` | 対話なしでデフォルト値を使用 |

#### 出力例

```
Minecraft version [1.21.4]: 
Loader [fabric]: 
Minecraft directory [~/.minecraft]: 

✓ Created config.toml
✓ Created projects.toml

Run `mcpax add <slug>` to add projects.
```

#### エラーケース

| 状況 | メッセージ | 終了コード |
|------|-----------|-----------|
| config.toml が既に存在 | `config.toml already exists. Use --force to overwrite.` | 1 |

---

### mcpax add \<slug\>

プロジェクトを管理対象に追加する。

```
mcpax add <slug>
```

#### 引数

| 引数 | 必須 | 説明 |
|------|------|------|
| `slug` | ✓ | Modrinth のプロジェクト slug |

#### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--version <ver>` | `-v` | バージョンを固定 |
| `--channel <ch>` | `-c` | リリースチャネル（release/beta/alpha） |

#### 動作

1. Modrinth API でプロジェクト情報を取得
2. プロジェクトの種類（mod/shader/resourcepack）を判定
3. `projects.toml` に追加
4. 結果を表示

#### 出力例

```
$ mcpax add sodium
✓ sodium (mod) を追加しました

Run `mcpax install sodium` to install.
```

#### エラーケース

| 状況 | メッセージ | 終了コード |
|------|-----------|-----------|
| プロジェクトが見つからない | `Project 'xxx' not found on Modrinth.` | 1 |
| 既に追加済み | `Project 'sodium' is already in the list.` | 1 |
| config.toml がない | `config.toml not found. Run 'mcpax init' first.` | 1 |

---

### mcpax remove \<slug\>

プロジェクトを管理対象から削除する。

```
mcpax remove <slug>
```

#### 引数

| 引数 | 必須 | 説明 |
|------|------|------|
| `slug` | ✓ | 削除するプロジェクトの slug |

#### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--delete-file` | `-d` | インストール済みファイルも削除 |
| `--yes` | `-y` | 確認をスキップ |

#### 動作

1. `projects.toml` から該当プロジェクトを検索
2. 確認プロンプトを表示（`--yes` がない場合）
3. `projects.toml` から削除
4. `--delete-file` の場合、ファイルも削除

#### 出力例

```
$ mcpax remove sodium
Remove sodium from the list? [y/N]: y
✓ sodium を削除しました
```

```
$ mcpax remove sodium --delete-file
Remove sodium from the list? [y/N]: y
Delete installed file? [y/N]: y
✓ sodium を削除しました
✓ sodium-fabric-0.6.0+mc1.21.4.jar を削除しました
```

#### エラーケース

| 状況 | メッセージ | 終了コード |
|------|-----------|-----------|
| プロジェクトがリストにない | `Project 'xxx' is not in the list.` | 1 |

---

### mcpax list

管理対象のプロジェクト一覧を表示する。

```
mcpax list
```

#### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--type <type>` | `-t` | 種類でフィルタ（mod/shader/resourcepack） |
| `--status <status>` | `-s` | 状態でフィルタ（installed/not-installed/outdated） |
| `--json` | | JSON 形式で出力 |

#### 動作

1. `projects.toml` を読み込む
2. 各プロジェクトのインストール状態を確認
3. 一覧を表示

#### 出力例

```
$ mcpax list

MOD (3):
  ✓ fabric-api      0.97.0    installed
  ✓ sodium          0.6.0     installed
  ○ lithium         -         not installed

Shader (1):
  ✓ complementary-reimagined  r5.2.2  installed

Resource Pack (1):
  ⚠ faithful-64x    1.20.0    outdated → 1.21.0
```

#### ステータスアイコン

| アイコン | 意味 |
|---------|------|
| ✓ | インストール済み（最新） |
| ○ | 未インストール |
| ⚠ | 更新あり |
| ✗ | 対応バージョンなし |

---

### mcpax search \<query\>

Modrinth でプロジェクトを検索する。

```
mcpax search <query>
```

#### 引数

| 引数 | 必須 | 説明 |
|------|------|------|
| `query` | ✓ | 検索キーワード |

#### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--type <type>` | `-t` | 種類でフィルタ（mod/shader/resourcepack） |
| `--limit <n>` | `-l` | 表示件数（デフォルト: 10） |

#### 動作

1. Modrinth API で検索
2. 結果を表示

#### 出力例

```
$ mcpax search sodium

Search results for "sodium":

1. sodium (mod)
   Modern rendering engine and target for optimization
   Downloads: 12,345,678

2. sodium-extra (mod)
   Extra options for Sodium
   Downloads: 1,234,567

3. reese-sodium-options (mod)
   Alternative options menu for Sodium
   Downloads: 987,654

Run `mcpax add <slug>` to add a project.
```

---

### mcpax update

更新を確認し、適用する。

```
mcpax update [options]
```

#### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--check` | `-c` | 確認のみ（ダウンロードしない） |
| `--yes` | `-y` | 確認をスキップして全て更新 |

#### 動作（--check あり）

1. `config.toml` と `projects.toml` を読み込む
2. 各プロジェクトについて Modrinth API で最新バージョンを確認
3. ローカルのファイルと比較
4. 結果を表示

#### 動作（--check なし）

1. 更新確認（上記と同じ）
2. 更新があるプロジェクトをダウンロード
3. ハッシュ検証
4. 古いファイルをバックアップ
5. 新しいファイルを配置

#### 出力例（--check）

```
$ mcpax update --check

Checking for updates...

Updates available (2):
  sodium         0.5.0 → 0.6.0
  lithium        0.12.0 → 0.12.1

Not compatible (1):
  some-mod       (no version for 1.21.4)

Up to date (5):
  fabric-api, iris, ...

Run `mcpax update` to apply updates.
```

#### 出力例（更新適用）

```
$ mcpax update

Checking for updates...

Updates available (2):
  sodium         0.5.0 → 0.6.0
  lithium        0.12.0 → 0.12.1

Apply updates? [Y/n]: y

Downloading...
  [████████████████████] sodium 0.6.0
  [████████████████████] lithium 0.12.1

✓ 2 projects updated
```

#### エラーケース

| 状況 | メッセージ | 終了コード |
|------|-----------|-----------|
| ハッシュ不一致 | `Hash mismatch for sodium. Download may be corrupted.` | 1 |
| ネットワークエラー | `Network error. Please check your connection.` | 1 |

---

### mcpax install

プロジェクトをインストールする。

```
mcpax install [slug] [options]
```

#### 引数

| 引数 | 必須 | 説明 |
|------|------|------|
| `slug` | - | インストールするプロジェクトの slug |

#### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--all` | `-a` | 全プロジェクトをインストール |

#### 動作

1. 対象プロジェクトを特定（slug 指定 or 全て）
2. 未インストールのプロジェクトをダウンロード
3. ハッシュ検証
4. 適切なディレクトリに配置

#### 出力例

```
$ mcpax install sodium

Downloading...
  [████████████████████] sodium 0.6.0

✓ sodium 0.6.0 をインストールしました
  → ~/.minecraft/mods/sodium-fabric-0.6.0+mc1.21.4.jar
```

```
$ mcpax install --all

Installing 5 projects...

Downloading...
  [████████████████████] fabric-api 0.97.0
  [████████████████████] sodium 0.6.0
  [████████████████████] lithium 0.12.1
  [████████████████████] complementary-reimagined r5.2.2
  [████████████████████] faithful-64x 1.21.0

✓ 5 projects installed
```

#### エラーケース

| 状況 | メッセージ | 終了コード |
|------|-----------|-----------|
| slug もオプションもなし | `Specify a slug or use --all` | 1 |
| プロジェクトがリストにない | `Project 'xxx' is not in the list. Use 'mcpax add' first.` | 1 |
| 対応バージョンなし | `No compatible version found for sodium (1.21.4 + fabric)` | 1 |

---

## 共通オプション

全コマンドで使用可能なオプション。

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--help` | `-h` | ヘルプを表示 |
| `--version` | `-V` | バージョンを表示 |
| `--config <path>` | | config.toml のパスを指定 |
| `--quiet` | `-q` | 出力を最小限に |
| `--verbose` | | 詳細な出力 |

---

## 終了コード

| コード | 意味 |
|-------|------|
| 0 | 正常終了 |
| 1 | エラー終了 |
| 2 | 引数エラー |

---

## 設定ファイルの探索順序

1. `--config` オプションで指定されたパス
2. カレントディレクトリの `config.toml`
3. （将来）`~/.config/mcpax/config.toml`

`projects.toml` は `config.toml` と同じディレクトリに配置する。
