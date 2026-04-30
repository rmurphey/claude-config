#!/usr/bin/env bash
# Creates .claude/BACKLOG.md with the correct structure if it doesn't already exist.
# Safe to run repeatedly — exits without changes if the file already exists.

set -euo pipefail

PROJECT_ROOT="$(cd "${1:-.}" && pwd)"
BACKLOG_DIR="${PROJECT_ROOT}/.claude"
BACKLOG_FILE="${BACKLOG_DIR}/BACKLOG.md"

if [[ -f "$BACKLOG_FILE" ]]; then
  exit 0
fi

mkdir -p "$BACKLOG_DIR"

cat > "$BACKLOG_FILE" << 'EOF'
# Backlog

> **Legend.** Priority: 🔴 Urgent · 🟠 High · 🟡 Normal · 🟢 Low. Status: `[ ]` pending · `[~]` in progress · `[!]` blocked · `[x]` done. Type tags: `[fix]` bug · `[feat]` new feature · `[code]` refactor · `[test]` tests · `[docs]` documentation · `[chore]` config/deps · `[research]` investigation · `[review]` code review.
>
> **How it works.** `/workflow` picks the highest pending task, creates a `wf/NNN-slug` branch in a worktree at `.worktrees/`, does the work, marks `[x]`. Branches await your manual merge. Full spec: `~/.claude/skills/workflow/SKILL.md`.

<!-- empty-checks: 0 -->

## 🔴 Urgent

## 🟠 High

## 🟡 Normal

## 🟢 Low

## 💭 Wishlist

## In Progress

## Blocked

## Done

EOF

echo "Created ${BACKLOG_FILE}"
