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
    └── mcpax/
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
class SearchResult:
    """検索結果"""
    hits: list[ModrinthProject]
    offset: int
    limit: int
    total_hits: int

@dataclass
class InstalledFile:
    """インストール済みファイル情報"""
    slug: str
    project_type: ProjectType
    filename: str
    version_id: str
    version_number: str
    sha512: str
    installed_at: datetime
    file_path: Path

@dataclass
class StateFile:
    """状態管理ファイル構造"""
    version: int = 1
    files: dict[str, InstalledFile] = {}

@dataclass
class UpdateResult:
    """更新適用の結果"""
    successful: list[str]  # 成功したプロジェクトのslug
    failed: list[tuple[str, str]]  # (slug, エラーメッセージ)
    backed_up: list[Path]  # バックアップされたファイルパス
```

### 3.2 core/api.py

Modrinth API クライアント。

```python
from dataclasses import dataclass

@dataclass
class RateLimitInfo:
    """Rate limit tracking information."""
    remaining: int
    limit: int
    reset: int  # Unix timestamp

class ModrinthClient:
    """Async client for Modrinth API v2."""

    BASE_URL = "https://api.modrinth.com/v2"
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 1.0

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        """Initialize the client."""
        ...

    @property
    def rate_limit_info(self) -> RateLimitInfo | None:
        """Current rate limit information.

        Returns None when:
        - No API request has been made yet
        - Response headers lack rate limit information
        - Using an externally injected client without rate limit tracking
        """
        ...

    async def get_project(self, slug: str) -> ModrinthProject:
        """プロジェクト情報を取得"""
        ...

    async def get_versions(self, slug: str) -> list[ProjectVersion]:
        """バージョン一覧を取得"""
        ...

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchResult:
        """プロジェクトを検索"""
        ...

    def filter_compatible_versions(
        self,
        versions: list[ProjectVersion],
        minecraft_version: str,
        loader: Loader,
        channel: ReleaseChannel = ReleaseChannel.RELEASE,
    ) -> list[ProjectVersion]:
        """MC バージョン・Loader に対応するバージョンをフィルタ"""
        ...

    def get_latest_compatible_version(
        self,
        versions: list[ProjectVersion],
        minecraft_version: str,
        loader: Loader,
        channel: ReleaseChannel = ReleaseChannel.RELEASE,
    ) -> ProjectVersion | None:
        """最新の互換バージョンを取得"""
        ...
```

### 3.3 core/downloader.py

ファイルダウンロード処理と SHA512 ハッシュ検証。

#### データクラス

```python
@dataclass
class DownloaderConfig:
    """Downloader の設定"""
    max_concurrent: int = 5  # 最大同時ダウンロード数
    chunk_size: int = 8192  # ストリーミングチャンクサイズ
    timeout: float = 300.0  # タイムアウト（秒）
    verify_hash: bool = True  # ハッシュ検証を行うか
```

#### プロトコル（進捗コールバック）

```python
class ProgressCallback(Protocol):
    """進捗更新コールバック"""
    def __call__(
        self,
        task_id: object,
        completed: int,
        total: int | None,
    ) -> None: ...

class TaskStartCallback(Protocol):
    """タスク開始コールバック"""
    def __call__(
        self,
        slug: str,
        version_number: str,
        total: int | None,
    ) -> object: ...

class TaskCompleteCallback(Protocol):
    """タスク完了コールバック"""
    def __call__(
        self,
        task_id: object,
        success: bool,
        error: str | None,
    ) -> None: ...
```

#### メインクラス

```python
class Downloader:
    """非同期ファイルダウンローダー"""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        config: DownloaderConfig | None = None,
        on_task_start: TaskStartCallback | None = None,
        on_progress: ProgressCallback | None = None,
        on_task_complete: TaskCompleteCallback | None = None,
    ) -> None:
        """初期化

        Args:
            client: 依存性注入用の httpx.AsyncClient（テスト用）
            config: ダウンローダー設定
            on_task_start: タスク開始時のコールバック
            on_progress: 進捗更新時のコールバック
            on_task_complete: タスク完了時のコールバック
        """
        ...

    async def download_file(self, task: DownloadTask) -> DownloadResult:
        """単一ファイルをダウンロード

        Args:
            task: ダウンロードタスク（URL、保存先、期待ハッシュ等）

        Returns:
            DownloadResult（成功/失敗、ファイルパス、エラーメッセージ）
        """
        ...

    async def download_all(
        self,
        tasks: list[DownloadTask],
    ) -> list[DownloadResult]:
        """複数ファイルを並列ダウンロード

        asyncio.Semaphore で同時実行数を制御

        Args:
            tasks: ダウンロードタスクのリスト

        Returns:
            DownloadResult のリスト（入力と同じ順序）
        """
        ...
```

#### ユーティリティ関数

```python
def compute_sha512(file_path: Path, chunk_size: int = 8192) -> str:
    """ファイルの SHA512 ハッシュを計算"""
    ...

def verify_file_hash(file_path: Path, expected_hash: str) -> bool:
    """ファイルハッシュを検証"""
    ...
```

#### 例外

```python
class DownloadError(MCPAXError):
    """ダウンロード失敗"""
    url: str | None  # エラーの原因となった URL

class HashMismatchError(DownloadError):
    """ハッシュ不一致（ファイルは自動削除される）"""
    filename: str
    expected: str
    actual: str
```

### 3.4 core/manager.py

プロジェクト管理のオーケストレーション層。設定、API、ダウンローダーを統合し、インストール・更新・削除などの高レベル操作を提供します。

#### 状態管理

インストール済みファイルの情報を `.mcpax-state.json` で永続化します：

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

#### クラス定義

```python
class ProjectManager:
    """プロジェクト管理のオーケストレーター（async context manager）"""

    STATE_FILE_NAME = ".mcpax-state.json"
    BACKUP_DIR_NAME = ".mcpax-backup"
    STATE_VERSION = 1

    def __init__(
        self,
        config: AppConfig,
        api_client: ModrinthClient | None = None,
        downloader: Downloader | None = None,
    ) -> None:
        """初期化

        Args:
            config: アプリケーション設定
            api_client: 依存性注入用のAPIクライアント（省略時は自動作成）
            downloader: 依存性注入用のダウンローダー（省略時は自動作成）
        """
        ...

    async def __aenter__(self) -> Self:
        """非同期コンテキストマネージャー（入口）"""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """非同期コンテキストマネージャー（出口）"""
        ...

    # ファイル管理機能 (F-401 to F-404)

    def get_target_directory(self, project_type: ProjectType) -> Path:
        """プロジェクト種別に応じた配置先ディレクトリを判定

        Args:
            project_type: プロジェクト種別

        Returns:
            配置先ディレクトリのパス
        """
        ...

    async def place_file(self, src: Path, dest_dir: Path) -> Path:
        """ダウンロードしたファイルを適切なディレクトリに配置

        Args:
            src: ソースファイルパス
            dest_dir: 配置先ディレクトリ

        Returns:
            配置後のファイルパス
        """
        ...

    async def backup_file(
        self,
        file_path: Path,
        backup_dir: Path | None = None,
    ) -> Path:
        """更新前のファイルをバックアップ

        Args:
            file_path: バックアップ対象ファイル
            backup_dir: バックアップ先（デフォルト: .mcpax-backup）

        Returns:
            バックアップファイルのパス
        """
        ...

    async def delete_file(self, file_path: Path) -> bool:
        """指定したファイルを削除

        Args:
            file_path: 削除対象ファイル

        Returns:
            削除成功時True、ファイルが存在しなかった場合False
        """
        ...

    # ステータス確認機能 (F-405, F-406)

    async def get_installed_file(self, slug: str) -> InstalledFile | None:
        """slugからインストール済みファイルを特定

        Args:
            slug: プロジェクトslug

        Returns:
            インストール済みファイル情報（未インストールの場合None）
        """
        ...

    async def get_install_status(self, slug: str) -> InstallStatus:
        """プロジェクトのインストール状態を確認

        Args:
            slug: プロジェクトslug

        Returns:
            インストール状態（NOT_INSTALLED/INSTALLED/OUTDATED/NOT_COMPATIBLE）
        """
        ...

    # 更新管理機能 (F-501 to F-503)

    def needs_update(
        self,
        installed: InstalledFile,
        latest: ProjectFile | None,
    ) -> bool:
        """ローカルとリモートのバージョンを比較

        Args:
            installed: インストール済みファイル情報
            latest: 最新ファイル情報

        Returns:
            更新が必要な場合True
        """
        ...

    async def check_updates(
        self,
        projects: list[ProjectConfig],
    ) -> list[UpdateCheckResult]:
        """各プロジェクトの更新有無を確認

        Args:
            projects: プロジェクト設定リスト

        Returns:
            更新確認結果のリスト
        """
        ...

    async def apply_updates(
        self,
        updates: list[UpdateCheckResult],
        backup: bool = True,
    ) -> UpdateResult:
        """更新があるプロジェクトをダウンロード・配置

        Args:
            updates: 更新対象リスト
            backup: バックアップするか（デフォルト: True）

        Returns:
            更新結果（成功/失敗/バックアップリスト）
        """
        ...
```

#### 使用例

```python
from mcpax.core.config import load_config, load_projects
from mcpax.core.manager import ProjectManager

# 設定とプロジェクトリストを読み込み
config = load_config()
projects = load_projects()

# async context managerとして使用
async with ProjectManager(config) as manager:
    # 更新確認
    updates = await manager.check_updates(projects)

    # 更新適用
    result = await manager.apply_updates(updates)

    print(f"成功: {result.successful}")
    print(f"失敗: {result.failed}")
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
class MCPAXError(Exception):
    """基底例外クラス"""
    pass

class APIError(MCPAXError):
    """一般的な API エラー"""
    def __init__(self, message: str, status_code: int | None = None) -> None:
        ...
    status_code: int | None

class ProjectNotFoundError(APIError):
    """プロジェクトが見つからない（404）"""
    def __init__(self, slug: str) -> None:
        ...
    slug: str

class RateLimitError(APIError):
    """レートリミット超過（429）"""
    def __init__(self, retry_after: int | None = None) -> None:
        ...
    retry_after: int | None

class DownloadError(MCPAXError):
    """ダウンロード失敗"""
    def __init__(self, message: str, url: str | None = None) -> None:
        ...
    url: str | None

class HashMismatchError(DownloadError):
    """ハッシュ検証失敗（ファイルは自動削除される）"""
    def __init__(self, filename: str, expected: str, actual: str) -> None:
        ...
    filename: str
    expected: str
    actual: str

class StateFileError(MCPAXError):
    """状態ファイルの読み書きエラー"""
    def __init__(self, message: str, path: Path | None = None) -> None:
        ...
    path: Path | None

class FileOperationError(MCPAXError):
    """ファイル操作エラー（移動、削除、バックアップ）"""
    def __init__(self, message: str, path: Path | None = None) -> None:
        ...
    path: Path | None
```

### 6.2 リトライ方針

- ネットワークエラー: 最大 3 回、指数バックオフ
- レートリミット: `X-Ratelimit-Reset` ヘッダを参照して待機
- 404 エラー: リトライしない（プロジェクトが存在しない）
