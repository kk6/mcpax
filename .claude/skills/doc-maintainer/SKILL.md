---
name: doc-maintainer
description: >
  Maintain project documentation by extracting specifications from test cases and implementation
  code. Creates or updates README, CLI usage guides, TUI guides, and API references using tests
  as the source of truth. Use this skill when the user asks to update docs, check if docs are
  outdated, write documentation for a feature, generate a usage guide, or sync docs with code.
  Also trigger for phrases like "ドキュメントを更新して", "READMEが古くなってないか", "この機能の
  ドキュメントを書いて", "docsを最新にして", "使い方を書いて", "doc maintenance",
  "sync documentation", "generate docs from tests". This skill should also be considered when
  preparing a PR that changes CLI commands, TUI screens, or public APIs — documentation may
  need updating alongside the code.
---

# Doc Maintainer

Documentation drifts. Tests don't. This skill uses passing tests and implementation code as the
authoritative source to create and maintain accurate documentation.

## Output Language

Documentation output MUST match the language of the existing document being updated. For new
documents, use Japanese (matching this project's README and docs/ convention). Only code
identifiers remain in English.

## Core Principle

Tests are verified specifications — every passing test is a proven statement about how the
software behaves. When documentation contradicts a test, the documentation is wrong. This skill
extracts facts from tests and translates them into human-readable documentation.

## What This Skill Does

1. **Update existing docs** — Find discrepancies between docs and current code/tests, fix them
2. **Create new docs** — Generate documentation for features that lack it
3. **Check freshness** — Report what's outdated without modifying anything

## Scope Resolution

| User says | Action |
|-----------|--------|
| "ドキュメントを更新して" / "update docs" | Check all docs for staleness, update what's outdated |
| "READMEを更新して" | Focus on README.md only |
| "CLIのドキュメントを書いて" | Generate/update CLI usage documentation |
| "TUIのドキュメントを書いて" | Generate/update TUI documentation |
| "この機能のドキュメントを書いて" + context | Generate docs for the specific feature |
| "ドキュメントが古くなってないかチェック" | Freshness check only — report, don't edit |

## Process

### Step 1: Identify Target Documents

Determine which documents are in scope. The project has:

- `README.md` — Project overview, installation, CLI usage examples, TUI keybindings
- `docs/` — Detailed design documents (requirements, architecture, data models, etc.)

### Step 2: Extract Specifications from Tests

Read test files to extract factual specifications. Focus on:

#### CLI Specifications (from `tests/unit/test_cli.py`)
- **Available commands**: Each `Test<Command>` class represents a command
- **Command options/flags**: Test methods that exercise `--flag` or `--option` values
- **Output format**: Assertions on console output (success messages, error messages, tables)
- **Error behavior**: Tests that verify exit codes or error messages
- **Example invocations**: The `runner.invoke(app, [...])` calls are real usage examples

#### TUI Specifications (from `tests/unit/tui/`)
- **Available screens**: Each test file maps to a screen
- **Key bindings**: Tests that simulate key presses (`app.press("q")`, etc.)
- **Widget behavior**: Tests for tables, inputs, progress panels
- **Navigation flow**: Tests that verify screen transitions

#### Core API Specifications (from `tests/unit/test_*.py`)
- **Public methods**: Test classes map to public API surface
- **Parameters and defaults**: Test setup reveals expected parameter shapes
- **Return types**: Assertions reveal return value structure
- **Error conditions**: Exception tests reveal error contract

### Step 3: Extract from Implementation

Read source code to supplement test-derived specs with:
- **Docstrings**: Google-style docstrings on public functions
- **Type hints**: Parameter and return types
- **CLI decorators**: `@app.command()`, `typer.Option()`, `typer.Argument()` metadata
- **Default values**: From function signatures and Pydantic model definitions

### Step 4: Cross-Reference and Identify Discrepancies

Compare extracted specs against existing documentation:

| Check | How |
|-------|-----|
| Command list completeness | All commands in `cli/app.py` appear in README |
| Option/flag accuracy | Documented flags match `typer.Option()` definitions |
| Example accuracy | Documented examples match tested invocations |
| TUI keybinding accuracy | Listed keybindings match tested bindings |
| Default value accuracy | Documented defaults match code defaults |
| Error message accuracy | Documented error info matches test assertions |
| Feature status accuracy | "Phase" status in README matches actual implementation |

### Step 5: Generate or Update Documentation

#### For freshness checks (check-only mode)
Output a report:

```markdown
# ドキュメント鮮度レポート

## 要更新箇所

| ドキュメント | 箇所 | 問題 | 根拠 |
|-------------|------|------|------|
| README.md | CLI使い方セクション | `config set`コマンドが未記載 | test_cli.py:TestConfigSet で存在確認 |
| ... | ... | ... | ... |

## 最新の箇所

| ドキュメント | 箇所 | 確認方法 |
|-------------|------|---------|
| README.md | インストール手順 | pyproject.toml と一致 |
| ... | ... | ... |
```

#### For updates (edit mode)
Apply changes directly to the documents using the Edit tool. For each change:
1. State what's being changed and why
2. Reference the test or code that proves the change is correct
3. Make the edit

#### For new document creation
Use the Write tool. Structure depends on the document type:

**CLI Usage Guide**:
```markdown
# コマンドリファレンス

## mcpax <command>

<概要>

### 使い方

```bash
mcpax <command> [OPTIONS] [ARGS]
```

### オプション

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|

### 使用例

```bash
# <テストケースから抽出した実際の使用例>
```

### エラーケース

- <テストで確認されたエラー条件と表示されるメッセージ>
```

**TUI Guide**:
```markdown
# TUI ガイド

## 画面一覧

### <Screen名>

<概要>

#### キーバインド

| キー | アクション |
|------|-----------|

#### 操作例

<テストから抽出した操作フロー>
```

**Diagrams**: When documenting screen transitions, navigation flows, or state changes, use
Mermaid notation (`\`\`\`mermaid ... \`\`\``) rather than ASCII art. Mermaid diagrams render
correctly across different Markdown viewers and are less prone to layout breakage. Example:

```markdown
\`\`\`mermaid
graph TD
    A[MainScreen] -->|Enter| B[ProjectDetailScreen]
    A -->|s| C[SettingsScreen]
    A -->|Search + Enter| D[SearchScreen]
    D -->|a| E[VersionSelectScreen]
    D -->|Escape| A
\`\`\`
```

## Important Guidelines

- **Tests are truth.** If a test says `--no-cache` is a valid flag but the README doesn't list
  it, add it to the README. If the README says `--verbose` exists but no test uses it, verify
  in the implementation before documenting.
- **Don't invent features.** Only document behavior that is either tested or clearly present in
  the implementation code. Never assume functionality exists based on naming alone.
- **Preserve document style.** When updating existing docs, match the surrounding formatting,
  heading level, and tone. The README uses Japanese — keep it that way.
- **Include line references.** When reporting discrepancies, reference the specific test or
  source file and line number (e.g., `test_cli.py:245`) so the reader can verify.
- **Keep examples realistic.** Usage examples should come from actual test invocations
  (`runner.invoke(app, ["add", "sodium"])` → `mcpax add sodium`). Don't make up examples.
- **Track test counts carefully.** The README includes test count tables. When updating, run
  the actual tests or count test functions to get accurate numbers.
- **Update status indicators.** Phase status (✅, 🧪, etc.) should reflect reality. If TUI
  tests exist and pass, the status should indicate that.
