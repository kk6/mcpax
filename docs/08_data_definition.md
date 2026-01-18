# データ定義

## 概要

このドキュメントは、mcpax で扱うデータの詳細を定義する。
概念データモデル（05_conceptual_data_model.md）を元に、具体的なデータ構造を整理した。

---

## エンティティ一覧

### ローカルデータ

| エンティティ | 説明 | 永続化 |
|-------------|------|--------|
| AppConfig | アプリケーション設定 | config.toml |
| ProjectConfig | プロジェクト設定 | projects.toml |
| InstalledFile | インストール済みファイル情報 | .mcpax-state.json |

### Modrinth API データ

| エンティティ | 説明 | 取得元 |
|-------------|------|--------|
| ModrinthProject | プロジェクト情報 | GET /project/{slug} |
| ProjectVersion | バージョン情報 | GET /project/{slug}/version |
| ProjectFile | ファイル情報 | ProjectVersion.files |
| SearchResult | 検索結果 | GET /search |

### 内部データ

| エンティティ | 説明 |
|-------------|------|
| UpdateCheckResult | 更新確認結果 |
| DownloadTask | ダウンロードタスク |
| DownloadResult | ダウンロード結果 |

---

## エンティティ詳細

### AppConfig

アプリケーション設定。config.toml から読み込む。

```python
@dataclass
class AppConfig:
    minecraft_version: str
    mod_loader: Loader
    minecraft_dir: Path
    mods_dir: Path
    shaders_dir: Path
    resourcepacks_dir: Path
    max_concurrent_downloads: int = 5
    verify_hash: bool = True
```

#### 属性

| 属性 | 型 | 必須 | デフォルト | 説明 |
|-----|-----|------|-----------|------|
| minecraft_version | str | ✓ | - | Minecraft バージョン（例: "1.21.4"） |
| mod_loader | Loader | ✓ | - | Mod Loader |
| minecraft_dir | Path | ✓ | - | Minecraft ディレクトリ |
| mods_dir | Path | - | {minecraft_dir}/mods | MOD 配置ディレクトリ |
| shaders_dir | Path | - | {minecraft_dir}/shaderpacks | Shader 配置ディレクトリ |
| resourcepacks_dir | Path | - | {minecraft_dir}/resourcepacks | Resource Pack 配置ディレクトリ |
| max_concurrent_downloads | int | - | 5 | 最大並列ダウンロード数 |
| verify_hash | bool | - | True | ハッシュ検証を行うか |

#### TOML 形式

```toml
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
# 以下は省略可能
# mods_dir = "~/.minecraft/mods"
# shaders_dir = "~/.minecraft/shaderpacks"
# resourcepacks_dir = "~/.minecraft/resourcepacks"

[download]
max_concurrent = 5
verify_hash = true
```

---

### ProjectConfig

プロジェクト設定。projects.toml の 1 エントリ。

```python
@dataclass
class ProjectConfig:
    slug: str
    version: str | None = None
    channel: ReleaseChannel = ReleaseChannel.RELEASE
    project_type: ProjectType
```

#### 属性

| 属性 | 型 | 必須 | デフォルト | 説明 |
|-----|-----|------|-----------|------|
| slug | str | ✓ | - | Modrinth のプロジェクト slug |
| version | str \| None | - | None | 固定するバージョン（None=最新） |
| channel | ReleaseChannel | - | RELEASE | リリースチャネル |
| project_type | ProjectType | ✓ | - | プロジェクト種別 |

#### TOML 形式

```toml
[[projects]]
slug = "fabric-api"
project_type = "mod"

[[projects]]
slug = "sodium"
project_type = "mod"
version = "0.6.0"  # バージョン固定

[[projects]]
slug = "some-mod"
project_type = "mod"
channel = "beta"  # ベータ版も許可
```

---

### InstalledFile

インストール済みファイル情報。.mcpax-state.json で管理。

```python
@dataclass
class InstalledFile:
    slug: str
    project_type: ProjectType
    filename: str
    version_id: str
    version_number: str
    sha512: str
    installed_at: datetime
    file_path: Path
```

#### 属性

| 属性 | 型 | 必須 | 説明 |
|-----|-----|------|------|
| slug | str | ✓ | プロジェクト slug |
| project_type | ProjectType | ✓ | プロジェクト種別 |
| filename | str | ✓ | ファイル名 |
| version_id | str | ✓ | Modrinth のバージョン ID |
| version_number | str | ✓ | バージョン番号 |
| sha512 | str | ✓ | ファイルの SHA512 ハッシュ |
| installed_at | datetime | ✓ | インストール日時 |
| file_path | Path | ✓ | ファイルの絶対パス |

#### JSON 形式

```json
{
  "version": 1,
  "files": {
    "sodium": {
      "slug": "sodium",
      "project_type": "mod",
      "filename": "sodium-fabric-0.6.0+mc1.21.4.jar",
      "version_id": "ABC123",
      "version_number": "0.6.0",
      "sha512": "abc123...",
      "installed_at": "2024-01-15T10:30:00Z",
      "file_path": "/Users/xxx/.minecraft/mods/sodium-fabric-0.6.0+mc1.21.4.jar"
    }
  }
}
```

---

### ModrinthProject

Modrinth のプロジェクト情報。

```python
@dataclass
class ModrinthProject:
    id: str
    slug: str
    title: str
    description: str
    project_type: ProjectType
    downloads: int
    icon_url: str | None
    versions: list[str]
```

#### 属性

| 属性 | 型 | 説明 |
|-----|-----|------|
| id | str | プロジェクト ID（Base62） |
| slug | str | URL 用のスラッグ |
| title | str | 表示名 |
| description | str | 説明文 |
| project_type | ProjectType | プロジェクト種別（mod/shader/resourcepack） |
| downloads | int | ダウンロード数 |
| icon_url | str \| None | アイコン URL |
| versions | list[str] | バージョン ID のリスト |

#### API レスポンス例

```json
{
  "id": "AANobbMI",
  "slug": "sodium",
  "project_type": "mod",
  "title": "Sodium",
  "description": "A modern rendering engine...",
  "downloads": 12345678,
  "icon_url": "https://...",
  "versions": ["ABC123", "DEF456", ...]
}
```

---

### ProjectVersion

プロジェクトのバージョン情報。

```python
@dataclass
class ProjectVersion:
    id: str
    project_id: str
    version_number: str
    version_type: ReleaseChannel
    game_versions: list[str]
    loaders: list[str]
    files: list[ProjectFile]
    dependencies: list[Dependency]
    date_published: datetime
```

#### 属性

| 属性 | 型 | 説明 |
|-----|-----|------|
| id | str | バージョン ID |
| project_id | str | プロジェクト ID |
| version_number | str | バージョン番号（例: "0.6.0"） |
| version_type | ReleaseChannel | リリースタイプ |
| game_versions | list[str] | 対応する MC バージョン |
| loaders | list[str] | 対応する Loader |
| files | list[ProjectFile] | ファイル一覧 |
| dependencies | list[Dependency] | 依存関係 |
| date_published | datetime | 公開日時 |

#### API レスポンス例

```json
{
  "id": "ABC123",
  "project_id": "AANobbMI",
  "version_number": "0.6.0",
  "version_type": "release",
  "game_versions": ["1.21.4", "1.21.3"],
  "loaders": ["fabric", "quilt"],
  "files": [...],
  "dependencies": [...],
  "date_published": "2024-01-15T10:00:00Z"
}
```

---

### ProjectFile

ダウンロード可能なファイル情報。

```python
@dataclass
class ProjectFile:
    url: str
    filename: str
    size: int
    sha512: str
    primary: bool
```

#### 属性

| 属性 | 型 | 説明 |
|-----|-----|------|
| url | str | ダウンロード URL |
| filename | str | ファイル名 |
| size | int | ファイルサイズ（バイト） |
| sha512 | str | SHA512 ハッシュ |
| primary | bool | プライマリファイルか |

#### API レスポンス例

```json
{
  "url": "https://cdn.modrinth.com/...",
  "filename": "sodium-fabric-0.6.0+mc1.21.4.jar",
  "size": 1234567,
  "hashes": {
    "sha512": "abc123..."
  },
  "primary": true
}
```

---

### SearchResult

検索結果。

```python
@dataclass
class SearchResult:
    hits: list[SearchHit]
    total_hits: int
    offset: int
    limit: int
```

```python
@dataclass
class SearchHit:
    slug: str
    title: str
    description: str
    project_type: ProjectType
    downloads: int
    icon_url: str | None
```

---

### UpdateCheckResult

更新確認結果。

```python
@dataclass
class UpdateCheckResult:
    slug: str
    status: InstallStatus
    current_version: str | None
    current_file: InstalledFile | None
    latest_version: str | None
    latest_file: ProjectFile | None
```

#### 属性

| 属性 | 型 | 説明 |
|-----|-----|------|
| slug | str | プロジェクト slug |
| status | InstallStatus | インストール状態 |
| current_version | str \| None | 現在のバージョン |
| current_file | InstalledFile \| None | 現在のファイル |
| latest_version | str \| None | 最新バージョン |
| latest_file | ProjectFile \| None | 最新ファイル |

---

### DownloadTask

ダウンロードタスク。

```python
@dataclass
class DownloadTask:
    url: str
    dest: Path
    expected_hash: str | None
    slug: str
    version_number: str
```

---

### DownloadResult

ダウンロード結果。

```python
@dataclass
class DownloadResult:
    task: DownloadTask
    success: bool
    file_path: Path | None
    error: str | None
```

---

## 列挙型

### Loader

```python
class Loader(str, Enum):
    FABRIC = "fabric"
    FORGE = "forge"
    NEOFORGE = "neoforge"
    QUILT = "quilt"
```

### ProjectType

```python
class ProjectType(str, Enum):
    MOD = "mod"
    SHADER = "shader"
    RESOURCEPACK = "resourcepack"
```

### ReleaseChannel

```python
class ReleaseChannel(str, Enum):
    RELEASE = "release"
    BETA = "beta"
    ALPHA = "alpha"
```

### InstallStatus

```python
class InstallStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    OUTDATED = "outdated"
    NOT_COMPATIBLE = "not_compatible"
```

---

## ER 図

```
┌─────────────────┐       ┌─────────────────┐
│   AppConfig     │       │  ProjectConfig  │
├─────────────────┤       ├─────────────────┤
│ minecraft_ver   │       │ slug            │
│ mod_loader      │       │ version         │
│ minecraft_dir   │       │ channel         │
│ mods_dir        │       └────────┬────────┘
│ shaders_dir     │                │
│ resourcepacks_  │                │ 1..* projects
│ dir             │                │
└─────────────────┘                ▼
                          ┌─────────────────┐
                          │  InstalledFile  │
                          ├─────────────────┤
                          │ slug            │◄──────────────┐
                          │ project_type    │               │
                          │ filename        │               │
                          │ version_id      │               │ slug で紐付け
                          │ version_number  │               │
                          │ sha512          │               │
                          │ installed_at    │               │
                          │ file_path       │               │
                          └─────────────────┘               │
                                                            │
┌─────────────────┐       ┌─────────────────┐               │
│ ModrinthProject │       │ ProjectVersion  │               │
├─────────────────┤       ├─────────────────┤               │
│ id              │       │ id              │               │
│ slug            │◄──────┤ project_id      │               │
│ title           │       │ version_number  │               │
│ description     │       │ version_type    │               │
│ project_type    │       │ game_versions   │               │
│ downloads       │       │ loaders         │◄──────────────┘
│ icon_url        │       │ files           │───┐
│ versions        │       │ dependencies    │   │
└─────────────────┘       │ date_published  │   │
                          └─────────────────┘   │
                                                │ 1..* files
                          ┌─────────────────┐   │
                          │   ProjectFile   │◄──┘
                          ├─────────────────┤
                          │ url             │
                          │ filename        │
                          │ size            │
                          │ sha512          │
                          │ primary         │
                          └─────────────────┘
```

---

## ファイル構成

```
.
├── config.toml           # AppConfig
├── projects.toml         # ProjectConfig[]
└── .mcpax-state.json       # InstalledFile[]
```

---

## データフロー

### 更新確認・インストール時

```
config.toml ──┐
              ├──► ProjectManager ──► Modrinth API
projects.toml ┘                              │
                                             ▼
                                    ProjectVersion[]
                                             │
.mcpax-state.json ◄──────────────────────────┬─┘
                                           │
                                           ▼
                                    UpdateCheckResult[]
                                           │
                                           ▼ (download)
                                    ~/.minecraft/mods/
                                    ~/.minecraft/shaderpacks/
                                    ~/.minecraft/resourcepacks/
```
