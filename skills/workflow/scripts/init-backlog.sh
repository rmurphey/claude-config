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

<!-- empty-checks: 0 -->

## 🔴 Urgent

## 🟠 High

## 🟡 Normal

## 🟢 Low

## In Progress

## Blocked

## Done

EOF

echo "Created ${BACKLOG_FILE}"
