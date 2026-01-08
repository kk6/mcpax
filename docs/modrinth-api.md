# Modrinth API 仕様メモ

このドキュメントは、本プロジェクトで使用する Modrinth API v2 のエンドポイントをまとめたものです。

公式ドキュメント: https://docs.modrinth.com/api/

## 1. 基本情報

### 1.1 ベース URL

- 本番: `https://api.modrinth.com/v2`
- ステージング: `https://staging-api.modrinth.com/v2`

### 1.2 認証

公開データの取得には認証不要。本プロジェクトでは認証が必要な操作は行わない。

### 1.3 User-Agent

**必須**。適切な User-Agent を設定しないとブロックされる可能性がある。

```
User-Agent: kk6/modrinth-mod-manager/0.1.0 (github.com/kk6)
```

### 1.4 レートリミット

- 300 リクエスト/分
- レスポンスヘッダで確認可能:
  - `X-Ratelimit-Limit`: 上限
  - `X-Ratelimit-Remaining`: 残り
  - `X-Ratelimit-Reset`: リセットまでの秒数

## 2. 使用するエンドポイント

### 2.1 プロジェクト取得

```
GET /project/{id|slug}
```

**レスポンス例:**

```json
{
  "id": "P7dR8mSH",
  "slug": "fabric-api",
  "project_type": "mod",
  "title": "Fabric API",
  "description": "Lightweight and modular API...",
  "body": "...",
  "categories": ["fabric", "library"],
  "client_side": "required",
  "server_side": "required",
  "versions": ["abc123", "def456", ...],
  "game_versions": ["1.21.4", "1.21.3", ...],
  "loaders": ["fabric", "quilt"],
  "downloads": 123456789,
  "icon_url": "https://...",
  "updated": "2024-01-15T12:00:00Z"
}
```

### 2.2 バージョン一覧取得

```
GET /project/{id|slug}/version
```

**クエリパラメータ:**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| loaders | JSON array | `["fabric"]`（MOD の場合のみ指定） |
| game_versions | JSON array | `["1.21.4"]` |
| featured | boolean | フィーチャー版のみ |

> **注意**: Shader や Resource Pack は Loader に依存しないため、`loaders` パラメータは省略する。

**リクエスト例:**

```
GET /project/fabric-api/version?loaders=["fabric"]&game_versions=["1.21.4"]
```

**レスポンス例:**

```json
[
  {
    "id": "abc123",
    "project_id": "P7dR8mSH",
    "name": "Fabric API 0.92.0",
    "version_number": "0.92.0+1.21.4",
    "changelog": "...",
    "game_versions": ["1.21.4"],
    "version_type": "release",
    "loaders": ["fabric"],
    "featured": true,
    "status": "listed",
    "date_published": "2024-01-15T12:00:00Z",
    "downloads": 12345,
    "files": [
      {
        "hashes": {
          "sha512": "93ecf5fe02914fb53d94aa...",
          "sha1": "a1b2c3d4e5..."
        },
        "url": "https://cdn.modrinth.com/data/.../fabric-api-0.92.0.jar",
        "filename": "fabric-api-0.92.0+1.21.4.jar",
        "primary": true,
        "size": 2048576
      }
    ],
    "dependencies": [
      {
        "version_id": null,
        "project_id": "xyz789",
        "file_name": null,
        "dependency_type": "optional"
      }
    ]
  }
]
```

### 2.3 複数プロジェクト取得

```
GET /projects?ids=["id1","id2","id3"]
```

一度に複数の MOD 情報を取得できる。最大 100 件。

### 2.4 プロジェクト検索

```
GET /search
```

**クエリパラメータ:**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| query | string | 検索クエリ |
| facets | JSON array | フィルター条件 |
| index | string | ソート順（relevance, downloads, follows, newest, updated） |
| offset | number | オフセット |
| limit | number | 件数（最大 100） |

**facets の書式:**

```
facets=[["categories:fabric"],["versions:1.21.4"],["project_type:mod"]]
```

- 内側の配列は OR
- 外側の配列は AND

**リクエスト例:**

```
GET /search?query=sodium&facets=[["categories:fabric"],["versions:1.21.4"],["project_type:mod"]]&limit=10
```

### 2.5 タグ一覧

ゲームバージョンや Loader の一覧を取得。

```
GET /tag/game_version   # MC バージョン一覧
GET /tag/loader         # Loader 一覧
GET /tag/category       # カテゴリ一覧
```

## 3. ファイルダウンロード

バージョン情報の `files[].url` から直接ダウンロード。CDN を使用しているため高速。

```
https://cdn.modrinth.com/data/{project_id}/versions/{version_id}/{filename}
```

### 3.1 ハッシュ検証

ダウンロード後、`files[].hashes.sha512` と照合してファイルの整合性を確認する。

```python
import hashlib

def verify_file(path: Path, expected_sha512: str) -> bool:
    sha512 = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha512.update(chunk)
    return sha512.hexdigest() == expected_sha512
```

## 4. 実装上の注意点

### 4.1 slug vs id

- `slug`: 人間が読みやすい識別子（例: `fabric-api`）。変更される可能性あり
- `id`: 内部識別子（例: `P7dR8mSH`）。不変

長期保存には `id` を使うべきだが、ユーザー入力は `slug` で受け付ける。

### 4.2 バージョン選択ロジック

1. `game_versions` と `loaders` でフィルタ
2. `version_type` で絞り込み（release > beta > alpha）
3. `date_published` が最新のものを選択
4. `files` の中から `primary: true` のファイルを選択

### 4.3 依存関係

`dependencies` には以下のタイプがある:

- `required`: 必須（自動インストール推奨）
- `optional`: オプション
- `incompatible`: 非互換
- `embedded`: 同梱済み

本プロジェクトでは `required` 依存の自動解決は将来機能として検討。

## 5. API レスポンスのキャッシュ

頻繁に変わらないデータはローカルキャッシュを検討:

- プロジェクト情報: 1 時間
- バージョン一覧: 15 分
- タグ一覧: 24 時間

初期実装ではキャッシュなしで進め、必要に応じて追加する。
