# アーキテクチャ設計書

## 1. 全体構成

```
mcpax/
├── pyproject.toml           # プロジェクト設定・依存関係
├── README.md
├── docs/                    # ドキュメント
│   ├── 01_project_charter.md
│   ├── 02_system_overview.md
│   ├── 03_requirements_list.md
│   ├── 04_user_scenarios.md
│   ├── 05_conceptual_data_model.md
│   ├── architecture.md
│   ├── modrinth-api.md
│   └── roadmap.md
├── config.toml              # ユーザー設定（実行時・カレントディレクトリ）
├── projects.toml            # プロジェクトリスト（実行時・カレントディレクトリ）
├── tests/                   # テスト
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_config.py
│   ├── test_downloader.py
│   └── test_manager.py
└── src/
    └── modrinth_mod_manager/
        ├── __init__.py
        ├── core/            # ビジネスロジック層
        │   ├── __init__.py
        │   ├── api.py
        │   ├── config.py
        │   ├── models.py
        │   ├── downloader.py
        │   └── manager.py
        ├── cli/             # CLI インターフェース
        │   ├── __init__.py
        │   └── app.py
        └── tui/             # TUI インターフェース（将来）
            ├── __init__.py
            └── app.py
```

## 2. レイヤー構成

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│  ┌─────────────────────────┐  ┌─────────────────────┐   │
│  │          CLI            │  │         TUI         │   │
│  │        (typer)          │  │      (textual)      │   │
│  └───────────┬─────────────┘  └──────────┬──────────┘   │
└──────────────┼───────────────────────────┼──────────────┘
               │                           │
               ▼                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Core Layer                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │                   Manager                        │    │
│  │  - プロジェクトリスト管理                         │    │
│  │  - 更新確認                                      │    │
│  │  - インストール制御                              │    │
│  └──────────────────────┬──────────────────────────┘    │
│                         │                                │
│  ┌──────────┐  ┌────────┴───────┐  ┌──────────────┐     │
│  │  Config  │  │   Downloader   │  │    Models    │     │
│  └──────────┘  └────────────────┘  └──────────────┘     │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Modrinth API Client                 │    │
│  │  - HTTP 通信 (httpx)                            │    │
│  │  - レートリミット制御                           │    │
│  │  - リトライ処理                                 │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## 3. モジュール詳細

### 3.1 core/models.py

データクラスの定義。

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Loader(str, Enum):
    FABRIC = "fabric"
    FORGE = "forge"
    NEOFORGE = "neoforge"
    QUILT = "quilt"

class ProjectType(str, Enum):
    MOD = "mod"
    SHADER = "shader"
    RESOURCEPACK = "resourcepack"

class ReleaseChannel(str, Enum):
    RELEASE = "release"
    BETA = "beta"
    ALPHA = "alpha"

@dataclass
class ProjectConfig:
    """プロジェクトリストの 1 エントリ"""
    slug: str
    version: str | None = None  # None = 最新版
    channel: ReleaseChannel = ReleaseChannel.RELEASE

@dataclass
class AppConfig:
    """アプリケーション設定"""
    minecraft_version: str
    loader: Loader
    minecraft_dir: Path
    mods_dir: Path
    shaders_dir: Path
    resourcepacks_dir: Path
    projects: list[ProjectConfig]

@dataclass
class ProjectFile:
    """ダウンロード対象のファイル情報"""
    url: str
    filename: str
    sha512: str
    size: int

@dataclass
class ProjectVersion:
    """プロジェクトのバージョン情報"""
    id: str
    version_number: str
    game_versions: list[str]
    loaders: list[str]
    files: list[ProjectFile]
    dependencies: list[dict]

@dataclass
class ModrinthProject:
    """Modrinth プロジェクト情報"""
    id: str
    slug: str
    title: str
    description: str
    project_type: ProjectType
    versions: list[str]

@dataclass
class InstalledFile:
    """インストール済みファイル情報"""
    filename: str
    hash: str
    project_slug: str
    installed_at: str
```

### 3.2 core/api.py

Modrinth API クライアント。

```python
class ModrinthClient:
    BASE_URL = "https://api.modrinth.com/v2"
    
    async def get_project(self, slug: str) -> ModrinthProject:
        """プロジェクト情報を取得"""
        ...
    
    async def get_versions(
        self,
        slug: str,
        game_versions: list[str] | None = None,
        loaders: list[str] | None = None,  # MOD の場合のみ指定
    ) -> list[ProjectVersion]:
        """バージョン一覧を取得"""
        ...
    
    async def search_projects(
        self,
        query: str,
        facets: list[list[str]] | None = None,
    ) -> list[ModrinthProject]:
        """プロジェクトを検索"""
        ...
```

### 3.3 core/downloader.py

ファイルダウンロード処理。

```python
class Downloader:
    async def download(
        self,
        url: str,
        dest: Path,
        expected_hash: str | None = None,
    ) -> Path:
        """ファイルをダウンロードし、ハッシュを検証"""
        ...
    
    async def download_many(
        self,
        files: list[ProjectFile],
        dest_dir: Path,
        max_concurrent: int = 5,
    ) -> list[Path]:
        """複数ファイルを並列ダウンロード"""
        ...
```

### 3.4 core/manager.py

プロジェクト管理のメインロジック。

```python
class ProjectManager:
    def __init__(self, config: AppConfig, client: ModrinthClient):
        ...
    
    def get_target_directory(self, project_type: ProjectType) -> Path:
        """プロジェクト種別に応じた配置先を返す"""
        match project_type:
            case ProjectType.MOD:
                return self.config.mods_dir
            case ProjectType.SHADER:
                return self.config.shaders_dir
            case ProjectType.RESOURCEPACK:
                return self.config.resourcepacks_dir
    
    async def check_updates(self) -> list[UpdateInfo]:
        """更新があるプロジェクトを確認"""
        ...
    
    async def install_all(self) -> InstallResult:
        """全プロジェクトをインストール"""
        ...
    
    async def install_project(self, slug: str) -> InstallResult:
        """特定のプロジェクトをインストール"""
        ...
    
    async def get_installed_projects(self) -> list[InstalledProject]:
        """インストール済みプロジェクト一覧を取得"""
        ...
```

### 3.5 cli/app.py

CLI エントリポイント。

```python
import typer

app = typer.Typer()

@app.command()
def init():
    """Initialize config files"""
    ...

@app.command()
def install(
    all: bool = typer.Option(False, "--all", "-a", help="Install all projects"),
    slug: str | None = typer.Argument(None, help="Project slug to install"),
):
    """Install projects from the list"""
    ...

@app.command()
def update(
    check: bool = typer.Option(False, "--check", "-c", help="Check only, don't install"),
):
    """Check and apply updates"""
    ...

@app.command()
def list():
    """List configured projects and their status"""
    ...

@app.command()
def add(slug: str):
    """Add a project to the list"""
    ...

@app.command()
def remove(slug: str):
    """Remove a project from the list"""
    ...

@app.command()
def search(query: str):
    """Search projects on Modrinth"""
    ...
```

## 4. 依存ライブラリ

| ライブラリ | 用途 | バージョン |
|-----------|------|-----------|
| httpx | HTTP クライアント（async 対応） | ^0.27 |
| typer | CLI フレームワーク | ^0.12 |
| rich | ターミナル出力装飾 | ^13.0 |
| textual | TUI フレームワーク（将来） | ^0.50 |

## 5. 設定ファイル形式

### 5.1 config.toml

```toml
[minecraft]
version = "1.21.4"
loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
# 以下は省略可能（デフォルトは minecraft_dir からの相対パス）
# mods_dir = "~/.minecraft/mods"
# shaders_dir = "~/.minecraft/shaderpacks"
# resourcepacks_dir = "~/.minecraft/resourcepacks"

[download]
max_concurrent = 5
verify_hash = true
```

### 5.2 projects.toml

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
channel = "beta"   # ベータ版も許可
```

## 6. エラーハンドリング方針

### 6.1 例外クラス

```python
class McpaxError(Exception):
    """基底例外クラス"""
    pass

class ProjectNotFoundError(McpaxError):
    """プロジェクトが見つからない"""
    pass

class VersionNotFoundError(McpaxError):
    """対応バージョンが見つからない"""
    pass

class DownloadError(McpaxError):
    """ダウンロード失敗"""
    pass

class HashMismatchError(DownloadError):
    """ハッシュ検証失敗"""
    pass

class RateLimitError(McpaxError):
    """レートリミット超過"""
    pass
```

### 6.2 リトライ方針

- ネットワークエラー: 最大 3 回、指数バックオフ
- レートリミット: `X-Ratelimit-Reset` ヘッダを参照して待機
- 404 エラー: リトライしない（プロジェクトが存在しない）
