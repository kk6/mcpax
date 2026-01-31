# Version Control (jj)

This project's primary development uses **jj (Jujutsu)** for version control. While external contributors may use git, AI agents and the core development team should use jj.

## Basic Workflow

1. **Create a bookmark for new work**:
   ```bash
   jj bookmark create feat/issue-XX-description
   ```

2. **Record changes with a commit message**:
   ```bash
   jj describe -m "type: description

   Detailed message here.

   Fixes #XX"
   ```

3. **Push to remote** (first time requires tracking):
   ```bash
   jj bookmark track feat/issue-XX-description --remote=origin
   jj git push --bookmark feat/issue-XX-description
   ```

4. **After PR is merged, fetch and start new work**:
   ```bash
   jj git fetch
   jj new main
   ```

## Release Branch Strategy (v2.0 Development)

**Context**: The current `main` branch represents v1.0 (stable). TUI features will be developed separately and released as v2.0. This strategy prevents work-in-progress code from entering `main` until v2.0 is complete.

**Bookmark Structure**:
- `main`: Always stable/released code (v1.0)
- `release/2.0`: Long-lived branch for v2.0 release candidate (aggregates all TUI work)
- `pr/<topic>`: Short-lived bookmarks for individual PRs

**Standard Workflow for v2.0 Features**:

1. Start from `main` (stable base):
   ```bash
   jj new main
   ```

2. Make changes and describe them (repeat as needed for small commits):
   ```bash
   # Make changes
   jj describe -m "feat: add TUI component X"
   jj new @  # Start next change if needed
   ```

3. When ready for PR, create a PR bookmark:
   ```bash
   jj bookmark create pr/<short-topic> -r @
   ```

4. Push and create PR targeting `release/2.0`:
   ```bash
   jj git push --bookmark pr/<short-topic>
   # Then create PR on GitHub: base=release/2.0, head=pr/<short-topic>
   ```

5. After PR is merged:
   ```bash
   jj git fetch
   jj new main  # Start next feature from stable base
   ```

**Exception: Hotfixes for v1.0**:

If a fix is needed for the current stable version (v1.0):

1. Start from `main`, make fix, create PR bookmark:
   ```bash
   jj new main
   # Make fix
   jj describe -m "fix: critical bug in X"
   jj bookmark create pr/hotfix-<short> -r @
   ```

2. Push and create PR targeting `main`:
   ```bash
   jj git push --bookmark pr/hotfix-<short>
   # Create PR: base=main, head=pr/hotfix-<short>
   ```

3. If the fix is also needed in v2.0, create a separate PR to `release/2.0` after the main PR merges.

## Claude Code Guidelines

- ✅ Create small, reviewable commits using `jj describe`
- ✅ Organize commit history before PR (squash/reword if needed)
- ✅ Create `pr/<topic>` bookmarks for PR submission
- ✅ Inform user of PR target (base branch) and push command
- ❌ Never execute `jj git push` (user handles push and PR creation)
- ❌ Never move the `main` bookmark
- ❌ Default PR target for v2.0 work is `release/2.0`, not `main`

**Information to Provide User** (at end of work):
- PR bookmark name (e.g., `pr/tui-core`)
- PR base target (`main` or `release/2.0`)
- Push command:
  ```bash
  jj git push --bookmark pr/<topic>
  ```

## Common Commands

| Command | Description |
|---------|-------------|
| `jj status` | Show working tree status |
| `jj log` | Show commit history |
| `jj diff` | Show changes |
| `jj new main` | Create a new change on top of main |
| `jj bookmark list` | List all bookmarks |
| `jj git fetch` | Fetch from remote |
| `jj git push --bookmark <name>` | Push specific bookmark to remote |
