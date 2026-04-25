# アーキテクチャ設計書

## 1. レイヤー構成

```mermaid
graph TD
    subgraph Presentation["Presentation Layer"]
        CLI["CLI (Typer)<br/>cli/"]
        TUI["TUI (Textual)<br/>tui/"]
    end

    subgraph Core["Core Layer"]
        PS["ProjectServices<br/>(lifecycle / DI)"]
        UC["UpdateChecker"]
        UA["UpdateApplier"]
        IP["InstallPlanner"]
        VR["VersionResolver"]
        FS["FileService"]
        SS["StateStore"]
        PU["ProjectUninstaller"]
        CM["Config / Models"]
    end

    subgraph Infra["Infrastructure"]
        MC["ModrinthClient<br/>(httpx)"]
        DL["Downloader<br/>(httpx + SHA-512)"]
        TOML["config.toml<br/>projects.toml"]
        JSON[".mcpax-state.json"]
        DISK["Minecraft filesystem"]
    end

    CLI --> PS
    TUI --> PS
    PS --> UC
    PS --> UA
    PS --> IP
    PS --> VR
    PS --> FS
    PS --> SS
    PS --> PU
    UC --> MC
    UC --> VR
    UC --> SS
    UA --> IP
    UA --> DL
    UA --> FS
    UA --> SS
    PU --> FS
    PU --> SS
    FS --> DISK
    SS --> JSON
    CM --> TOML
    MC --> |"Modrinth API v2"| Internet[(Internet)]
    DL --> Internet
```

CLI/TUI は `ProjectServices` 経由でのみ core を呼び出す。business logic は core に置き、Presentation Layer には置かない。

## 2. ディレクトリ構成

```text
mcpax/
├── pyproject.toml
├── src/
│   └── mcpax/
│       ├── core/                  # Business logic layer
│       │   ├── api.py             # Modrinth API client
│       │   ├── cache.py           # API response cache
│       │   ├── config.py          # Config file read/write
│       │   ├── downloader.py      # Download + SHA-512 verification
│       │   ├── exceptions.py      # Domain exceptions
│       │   ├── file_service.py    # File placement / backup / delete
│       │   ├── install_planner.py # Download task planning (pure)
│       │   ├── models.py          # Pydantic data models
│       │   ├── protocols.py       # Interface definitions (Protocol)
│       │   ├── services.py        # DI composition root
│       │   ├── state_store.py     # .mcpax-state.json persistence
│       │   ├── uninstaller.py     # Project uninstall
│       │   ├── update_applier.py  # Update execution
│       │   ├── update_checker.py  # Update check
│       │   └── version_resolver.py# Version selection logic
│       ├── cli/                   # CLI interface (Typer)
│       │   ├── app.py
│       │   ├── commands/          # add / remove / list / search / install / update / ...
│       │   ├── formatters.py
│       │   └── shared.py
│       └── tui/                   # TUI interface (Textual)
│           ├── app.py
│           ├── screens/           # main / search / detail / install / settings / ...
│           └── widgets/           # ProjectTable / SearchInput / ProgressPanel / ...
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_*.py              # Core unit tests
    │   └── tui/                   # TUI screen / widget tests
    └── fixtures/                  # config.toml / projects.toml
```

## 3. Core コンポーネント詳細

```mermaid
classDiagram
    class ProjectServices {
        +config: AppConfig
        +state_store: StateStore
        +file_service: FileService
        +version_resolver: VersionResolver
        +install_planner: InstallPlanner
        +update_checker: UpdateChecker
        +update_applier: UpdateApplier
        +__aenter__()
        +__aexit__()
    }

    class UpdateChecker {
        +check_updates(projects) UpdateCheckResult[]
        +check_single(project) UpdateCheckResult
    }

    class UpdateApplier {
        +apply_updates(results) UpdateResult
        +rollback()
    }

    class InstallPlanner {
        +create_plan(results) InstallPlan
    }

    class VersionResolver {
        +resolve(criteria) ProjectVersion
    }

    class FileService {
        +resolve_target_dir(project_type) Path
        +place_file(src, dst) Path
        +backup_file(path) Path
        +delete_file(path) RemoveResult
    }

    class StateStore {
        +load() StateFile
        +save(state)
        +get_installed_file(slug) InstalledFile
        +save_installed_file(slug, file)
        +remove_installed_file(slug)
    }

    class ProjectUninstaller {
        +uninstall(slug)
    }

    class ModrinthClient {
        +get_project(slug) ModrinthProject
        +get_versions(slug) ProjectVersion[]
        +search(query) SearchResult
    }

    class Downloader {
        +download_all(tasks) DownloadResult[]
    }

    ProjectServices --> UpdateChecker
    ProjectServices --> UpdateApplier
    ProjectServices --> InstallPlanner
    ProjectServices --> VersionResolver
    ProjectServices --> FileService
    ProjectServices --> StateStore
    ProjectServices --> ProjectUninstaller
    UpdateChecker --> ModrinthClient
    UpdateChecker --> VersionResolver
    UpdateChecker --> StateStore
    UpdateApplier --> InstallPlanner
    UpdateApplier --> Downloader
    UpdateApplier --> FileService
    UpdateApplier --> StateStore
    ProjectUninstaller --> FileService
    ProjectUninstaller --> StateStore
```

## 4. データフロー

### 更新確認 (update check)

```mermaid
sequenceDiagram
    actor User
    participant CLI/TUI
    participant UpdateChecker
    participant ModrinthClient
    participant VersionResolver
    participant StateStore

    User->>CLI/TUI: mcpax update --check
    CLI/TUI->>UpdateChecker: check_updates(projects)
    loop 各 project (並列)
        UpdateChecker->>ModrinthClient: get_project(slug)
        UpdateChecker->>ModrinthClient: get_versions(slug)
        UpdateChecker->>StateStore: get_installed_file(slug)
        UpdateChecker->>VersionResolver: resolve(criteria)
        VersionResolver-->>UpdateChecker: ProjectVersion
        UpdateChecker-->>UpdateChecker: hash 比較 / status 判定
    end
    UpdateChecker-->>CLI/TUI: UpdateCheckResult[]
    CLI/TUI-->>User: 更新状況を表示
```

### 更新適用 (update apply)

```mermaid
sequenceDiagram
    actor User
    participant CLI/TUI
    participant UpdateApplier
    participant InstallPlanner
    participant Downloader
    participant FileService
    participant StateStore

    User->>CLI/TUI: mcpax update
    CLI/TUI->>UpdateApplier: apply_updates(results)
    UpdateApplier->>InstallPlanner: create_plan(results)
    InstallPlanner-->>UpdateApplier: InstallPlan
    UpdateApplier->>Downloader: download_all(tasks)
    Downloader-->>UpdateApplier: DownloadResult[]
    loop 各 file
        UpdateApplier->>FileService: backup_file(old) or delete_file(old)
        UpdateApplier->>FileService: place_file(downloaded)
        UpdateApplier->>StateStore: save_installed_file(slug, file)
    end
    alt ダウンロード失敗
        UpdateApplier->>FileService: rollback (backup 復元)
    end
    UpdateApplier-->>CLI/TUI: UpdateResult
    CLI/TUI-->>User: 結果を表示
```

## 5. TUI 画面遷移

```mermaid
stateDiagram-v2
    [*] --> MainScreen : mcpax tui

    MainScreen --> InstallScreen : i (install)
    MainScreen --> SettingsScreen : s (settings)
    MainScreen --> ProjectDetailScreen : Enter (view detail)
    MainScreen --> SearchScreen : SearchInput に入力して Enter

    SearchScreen --> VersionSelectScreen : a (add project)
    VersionSelectScreen --> SearchScreen : Esc / 選択完了
    SearchScreen --> MainScreen : Esc

    ProjectDetailScreen --> MainScreen : Esc
    ProjectDetailScreen --> MainScreen : d (delete) → 確認ダイアログ後

    InstallScreen --> MainScreen : 完了後 / Esc
    SettingsScreen --> MainScreen : 保存後 / Esc
```

> Search 画面への遷移は専用キーではなく、Main 画面上の `SearchInput` ウィジェットにクエリを入力して Enter することで開く。

## 6. 設計方針

- **依存方向**: Presentation → Core のみ。逆方向は禁止
- **業務ロジックの配置**: CLI/TUI には置かない。Core に集中させる
- **副作用の分離**: `InstallPlanner` は pure function。副作用は `UpdateApplier` に限定
- **インフラ詳細の隠蔽**: HTTP / filesystem / TOML/JSON の詳細は Core 内の専用クラスに閉じる
- **テスタビリティ**: 外部依存 (API, filesystem) は `ProjectServices` が DI で注入。Protocol で境界を定義
- **段階的改善**: 大規模 rewrite ではなく Fowler-style の小さな refactoring を積み上げる

## 7. テスト対象と優先度

| モジュール | テスト観点 |
|---|---|
| `VersionResolver` | compatibility / channel / pinned version 解決ロジック |
| `InstallPlanner` | actionable update から download task 生成 (pure function) |
| `UpdateChecker` | update status 判定、pinned / non-pinned 結果生成 |
| `UpdateApplier` | download failure、partial success、backup、rollback |
| `FileService` | target directory 解決、place / backup / delete |
| `StateStore` | missing / corrupted state の load/save、installed file helpers |
