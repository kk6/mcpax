# Version Control (git)

This project uses **git** for version control. Development happens on `main`; feature work is done on short-lived feature branches and merged via PR.

## Basic Workflow

1. **Start from up-to-date `main`**:
   ```bash
   git switch main
   git pull --ff-only
   ```

2. **Create a feature branch**:
   ```bash
   git switch -c feat/issue-XX-description
   ```

   Branch naming convention:
   - `feat/issue-XX-<short-description>` — new features (XX = GitHub issue number)
   - `fix/issue-XX-<short-description>` — bug fixes tied to an issue
   - `fix/<short-description>` — bug fixes without an issue
   - `refactor/<short-description>`, `docs/<short-description>`, `chore/<short-description>` — other work
   - If there is no issue, omit the `issue-XX-` segment (e.g. `feat/tui-detail-screen`)

3. **Commit in small, reviewable units** using Conventional Commits:
   ```bash
   git add -p
   git commit -m "feat: add TUI component X

   Fixes #XX"
   ```

4. **Keep the branch up to date with main** (prefer rebase for a linear history):
   ```bash
   git fetch origin
   git rebase origin/main
   ```

5. **After PR merge, clean up locally**:
   ```bash
   git switch main
   git pull --ff-only
   git branch -d feat/issue-XX-description
   ```

## Claude Code Guidelines

- ✅ Create small, reviewable commits via `git commit`
- ✅ Organize commit history before PR (squash/rebase/reword as needed)
- ✅ Use `feat/issue-XX-*`, `fix/*`, `refactor/*`, `docs/*`, `chore/*` branch names
- ✅ Inform the user of the branch name and push command when work is ready
- ❌ Never execute `git push` (user handles push and PR creation)
- ❌ Never force-push to `main`, and never move `main` directly
- ❌ Never use `--no-verify` to bypass hooks; fix hook failures at the source
- ❌ Never `git commit --amend` a commit that has already been pushed/shared

**Information to provide the user** (at end of work):
- Branch name (e.g. `feat/issue-42-release-channel`)
- PR base target (`main`)
- Push command:
  ```bash
  git push -u origin feat/issue-XX-description
  ```

## Common Commands

| Command | Description |
|---------|-------------|
| `git status` | Show working tree status |
| `git log --oneline -20` | Show recent commit history |
| `git diff` / `git diff --staged` | Show unstaged / staged changes |
| `git switch -c feat/issue-XX-foo` | Create and switch to a new branch |
| `git switch main && git pull --ff-only` | Update local main |
| `git fetch origin && git rebase origin/main` | Rebase current branch onto latest main |
| `git branch -d <name>` | Delete a merged local branch |
