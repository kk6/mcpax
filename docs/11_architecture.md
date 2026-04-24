# アーキテクチャ設計書

## 1. 全体構成

```text
mcpax/
├── pyproject.toml
├── README.md
├── docs/
├── tests/
│   ├── fixtures/
│   └── unit/
└── src/
    └── mcpax/
        ├── core/
        │   ├── api.py
        │   ├── cache.py
        │   ├── config.py
        │   ├── downloader.py
        │   ├── file_service.py
        │   ├── install_planner.py
        │   ├── manager.py
        │   ├── models.py
        │   ├── state_store.py
        │   ├── update_applier.py
        │   ├── update_checker.py
        │   └── version_resolver.py
        ├── cli/
        └── tui/
```

## 2. レイヤー構成

```text
Presentation Layer
  CLI (Typer)
  TUI (Textual)
        |
        v
Core Layer
  ProjectManager facade
  UpdateChecker
  UpdateApplier
  InstallPlanner
  VersionResolver
  FileService
  StateStore
  Config / Models
        |
        v
Infrastructure-facing Components
  ModrinthClient (httpx)
  Downloader (httpx)
  TOML config files
  .mcpax-state.json
  Minecraft filesystem
```

CLI/TUI は core の public API を呼び出し、結果を表示する。更新判定、インストール計画、ファイル配置、状態保存などの業務ロジックは core に置く。

## 3. Core の責務

### `manager.py`

`ProjectManager` は後方互換性のための facade。CLI/TUI から既存の呼び出し口として使われるが、主要な判断や I/O は下位サービスへ委譲する。

主な委譲先:

- update check: `UpdateChecker`
- update apply: `UpdateApplier`
- version resolution: `VersionResolver`
- install planning: `InstallPlanner`
- file operations: `FileService`
- state persistence: `StateStore`

### `version_resolver.py`

Minecraft version、mod loader、shader loader、release channel、pinned version をもとに Modrinth versions から採用する version を解決する。

主な型:

- `VersionCriteria`
- `VersionResolver`

### `install_planner.py`

`UpdateCheckResult` の一覧から、実行すべき download task と計画時点の失敗を作る。副作用は持たない。

主な型:

- `InstallPlan`
- `InstallPlanner`

### `update_checker.py`

設定済み project について Modrinth API と state を照合し、`UpdateCheckResult` を作る。

担当する処理:

- 複数 project の並列 update check
- 単一 project の update check
- pinned / non-pinned の結果生成
- installed hash と latest file hash の比較
- install status 判定

### `update_applier.py`

`UpdateCheckResult` を実際に適用する。

担当する処理:

- install plan の作成
- downloader の実行
- downloaded file の配置
- old file の backup/delete
- state 更新
- rollback
- temporary download directory cleanup

### `file_service.py`

Minecraft ディレクトリ配下の配置先解決とファイル操作を担当する。

担当する処理:

- project type から target directory を解決
- downloaded file の配置
- timestamped backup
- delete

### `state_store.py`

`.mcpax-state.json` の永続化を担当する。

担当する処理:

- state file path の解決
- `StateFile` の load/save
- installed file の get/save/remove

### `api.py`

Modrinth API v2 の async client。HTTP 通信、retry、rate limit 情報、API response の model 化を担当する。

互換性のため version filtering 系メソッドも残しているが、実装は `VersionResolver` に委譲する。

### `downloader.py`

ファイルダウンロードと SHA-512 hash verification を担当する。複数 task の並列ダウンロードを提供する。

## 4. データフロー

### 更新確認

```text
CLI/TUI
  -> ProjectManager.check_updates()
  -> UpdateChecker.check_updates()
  -> ModrinthClient.get_project()/get_versions()
  -> StateStore.get_installed_file()
  -> VersionResolver
  -> UpdateCheckResult[]
```

### 更新適用

```text
CLI/TUI
  -> ProjectManager.apply_updates()
  -> UpdateApplier.apply_updates()
  -> InstallPlanner.create_plan()
  -> Downloader.download_all()
  -> FileService.place_file()/backup_file()/delete_file()
  -> StateStore.save()
  -> UpdateResult
```

## 5. 設計方針

このプロジェクトでは full DDD は採用しない。代わりに、軽量な Clean Architecture の考え方を使い、依存方向と責務分離を守る。

基本方針:

- CLI/TUI に業務ロジックを置かない
- HTTP、filesystem、TOML/JSON 永続化の詳細を一箇所に集中させる
- core service は小さく、単体テストしやすく保つ
- 既存 public API は必要に応じて facade として残す
- 大きな rewrite ではなく Fowler-style の小さな refactoring を積み上げる

## 6. テスト方針

重点的に単体テストする対象:

- `VersionResolver`: compatibility / channel / pinned version
- `InstallPlanner`: actionable update から download task 生成
- `UpdateChecker`: update status と pinned/non-pinned 結果
- `UpdateApplier`: download failure、partial success、backup、rollback
- `FileService`: target directory、place、backup、delete
- `StateStore`: missing/corrupted state、load/save、installed file helpers

`ProjectManager` のテストは facade としての互換性確認を中心にする。
