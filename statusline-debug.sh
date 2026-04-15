#!/bin/bash
# Debug version - logs input to see actual structure
input=$(cat)
echo "$input" > /tmp/statusline-debug.json
echo "$input" | jq '.' > /tmp/statusline-debug-pretty.json 2>&1
cat "$HOME/.claude/statusline-command.sh" | bash
