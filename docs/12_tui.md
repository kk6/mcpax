# TUI ガイド

## 概要

mcpax の TUI（Terminal UI）は Textual を使ったインタラクティブな操作画面です。CLI と同じ設定ファイルを使い、検索・追加・削除・更新・設定変更を画面上で行えます。

## 事前準備

TUI は optional dependency です。開発版を使う場合は追加で Textual をインストールしてください。

```bash
uv pip install -e ".[tui]"
```

`config.toml` と `projects.toml` が必要です。まだ作成していない場合は先に `mcpax init` を実行してください。

## 起動

```bash
mcpax tui
```

起動時に設定が見つからない場合はエラーメッセージで終了します。

## 主な画面

- Main: プロジェクト一覧 + 検索入力 + ステータス
- Search: Modrinth 検索結果（追加操作）
- Detail: プロジェクト詳細（削除操作）
- Install: インストール/更新の進捗とサマリー
- Settings: `config.toml` の編集

## キーバインド（抜粋）

Main:
- `q`: 終了
- `r`: 更新チェック
- `i`: 全プロジェクトのインストール/更新
- `s`: 設定画面
- `d`: 選択中プロジェクトを削除
- `D`: 互換性なしプロジェクトを一括削除
- `Enter`: 詳細表示

Search:
- `a`: 追加
- `Esc`: 戻る

Detail:
- `d`: 削除
- `Esc`: 閉じる

Install:
- `Esc`: キャンセル/閉じる

Settings:
- `Enter`: 編集
- `Esc`: 戻る

## 補足

- TUI は CLI と同じコアロジックを使用します。
- 追加したプロジェクトは `projects.toml` に保存されます。
- Main 画面と Detail 画面の削除操作は確認ダイアログを表示し、承認後に `projects.toml` から対象プロジェクトを削除します。
- Main 画面の `D` は現在の更新チェック結果で `NOT_COMPATIBLE` のプロジェクトだけを対象にします。
