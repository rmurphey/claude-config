---
name: push
description: Push local commits to the remote repository with safety checks. Verifies branch state, prevents force-push to main/master, and reports what was pushed.
---

# push

Push local commits to the remote with safety checks.

## How to invoke

```
/push
```

## What You Must Do

### Step 1: Check branch state

Run these commands in parallel:

- `git status` — verify working tree state
- `git log --oneline @{upstream}..HEAD 2>/dev/null || git log --oneline -5` — see commits that will be pushed
- `git branch --show-current` — get current branch name
- `git remote -v` — verify the remote

### Step 2: Safety checks

Before pushing, verify:

1. **Branch name**: if on `main` or `master`, warn the user and ask for confirmation before pushing directly
2. **Unpushed commits**: show the user exactly which commits will be pushed. If there are none, report "nothing to push" and stop
3. **Uncommitted changes**: if there are staged or unstaged changes, warn the user that these will not be included in the push. Ask if they want to commit first (suggest `/commit`)

### Step 3: Push

Push to the remote:

```
git push
```

If the branch has no upstream tracking branch:

```
git push -u origin <branch-name>
```

If the push is rejected (non-fast-forward), **do not force push**. Instead:
- Report the rejection
- Suggest `git pull --rebase` to incorporate remote changes
- Ask the user how they want to proceed

### Step 4: Auto-PR on first push

If the push used `-u` (first push to a new branch that is NOT `main` or `master`):

1. Ask the user if they want to create a draft PR
2. If yes, run: `gh pr create --draft --fill` to create a draft PR with auto-filled title and body
3. Report the PR URL

If the branch already had an upstream, skip this step.

### Step 5: Report results

After a successful push, show:
- The branch name and remote
- Which commits were pushed (hash and message)
- PR URL (if created in Step 4)
- Current `git status`

## Rules

- **Never force push**: no `--force`, no `--force-with-lease` unless the user explicitly requests it
- **Never bypass hooks**: no `--no-verify`
- **Never push secrets**: if `git status` shows `.env` or credential files staged, abort and warn
- **Always confirm before pushing to main/master**: direct pushes to the default branch deserve a confirmation prompt
- **Report clearly**: the user should know exactly what was pushed and where

## Architecture

- `SKILL.md` — This file (instruction-based skill, no executable)
