---
name: commit
description: Create atomic git commits from the current working tree. Analyzes all changes, groups them by logical topic, and creates one focused commit per topic with a conventional commit message. Never bypasses hooks.
---

# commit

Create atomic git commits from the current working tree.

## How to invoke

```
/commit
```

## What You Must Do

Follow these steps exactly. Do not skip steps or combine them.

### Step 1: Gather state

Run these commands in parallel:

- `git status` — see all modified, staged, and untracked files (never use `-uall`)
- `git diff` — see unstaged changes
- `git diff --cached` — see already-staged changes
- `git log --oneline -5` — see recent commit style

### Step 2: Analyze and group changes

Look at every changed file (staged + unstaged + untracked) and group them by **logical topic** — a single coherent change that belongs in one commit. A topic is defined by what it accomplishes, not by file type or directory.

Grouping rules:
- A bug fix and its test belong in the same commit
- A new feature, its tests, and its documentation belong in the same commit
- Config changes that support a feature belong with that feature
- Unrelated formatting/cleanup changes are a separate commit
- Dependency changes unrelated to a feature are a separate commit
- If ALL changes are part of one logical topic, make one commit

For each group, determine:
- Which files to stage
- The conventional commit prefix (`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`)
- A concise commit message (1-2 sentences) focused on the "why"

### Step 3: Decide whether to proceed or ask

**Single commit (all changes are one topic):**
Proceed immediately — do NOT ask for approval. The user trusts the conventional-commit prefix and the atomic-commit hook to catch mistakes. Just create the commit and report results.

**Multiple commits (changes span more than one topic):**
You MUST present the commit plan and wait for explicit approval before proceeding. Show the plan:

```
Commit plan (2 commits — approval required):
1. feat: add user validation endpoint
   - src/routes/users.ts, src/validators/user.ts, tests/users.test.ts
2. chore: update eslint config for new rules
   - .eslintrc.json
```

The user may adjust the grouping, merge groups, or reorder. Do not proceed until they approve.

**Edge cases:**
- If you are uncertain whether changes are one topic or two, err on the side of one commit (the atomic-commit hook will block if it disagrees)
- If a single commit touches 3+ unrelated directories but is genuinely one topic (e.g., a cross-cutting refactor), proceed without asking — the commit message should make the unity clear

### Step 4: Create commits

For each group, in order:

1. Stage only the files for this group: `git add <file1> <file2> ...`
   - Never use `git add -A` or `git add .`
   - Do not stage files that contain secrets (`.env`, credentials, tokens) — warn the user instead
2. Create the commit using `-m` flags (not heredoc, to avoid governance hook false positives):
   ```
   git commit -m "prefix: short description" -m "Longer explanation if needed." -m "Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
   ```
3. Verify the commit succeeded with `git status`

If a pre-commit hook fails:
- Read the error output
- Fix the issue
- Re-stage the affected files
- Create a **new** commit (never amend)

### Step 5: Report results

After all commits are created, show:
- Each commit hash and message
- Current `git status` (should be clean, or show remaining untracked files)
- Number of commits ahead of remote

## Rules

- **Never bypass hooks**: no `--no-verify`, no `--no-gpg-sign`
- **Never amend**: always create new commits
- **Never stage secrets**: warn on `.env`, `credentials.*`, `*_key`, `*.pem`
- **Always use conventional commits**: `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`
- **Always include Co-Authored-By**: append as the final `-m` flag
- **Use `-m` flags for messages**: avoid heredoc/`$(cat ...)` patterns which can trigger the governance hook
- **Atomic means one topic**: if the enforce-atomic-commits hook blocks a commit, split it further rather than bypassing

## Architecture

- `SKILL.md` — This file (instruction-based skill, no executable)
