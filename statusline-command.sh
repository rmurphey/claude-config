#!/bin/bash

# Get current directory and model from JSON input
input=$(cat)
cwd=$(echo "$input" | jq -r '.workspace.current_dir')
model=$(echo "$input" | jq -r '.model // "unknown"')

# Shorten model name for display
case "$model" in
    *"sonnet"*) model_short="sonnet" ;;
    *"opus"*) model_short="opus" ;;
    *"haiku"*) model_short="haiku" ;;
    *) model_short="$model" ;;
esac

# Get git branch and stats if in a git repo
git_info=""
uncommitted_lines=""
if cd "$cwd" 2>/dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git -c core.useBuiltinFSMonitor=false symbolic-ref --short HEAD 2>/dev/null || git -c core.useBuiltinFSMonitor=false rev-parse --short HEAD 2>/dev/null)
    if [ -n "$branch" ]; then
        git_info=" ($branch)"
    fi

    # Count uncommitted lines (insertions + deletions)
    diff_stats=$(git diff --shortstat 2>/dev/null)
    if [ -n "$diff_stats" ]; then
        insertions=$(echo "$diff_stats" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo "0")
        deletions=$(echo "$diff_stats" | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo "0")

        # Format with color: green for additions, red for deletions
        # ANSI: \033[32m = green, \033[31m = red, \033[0m = reset
        uncommitted_parts=""
        if [ "$insertions" -gt 0 ]; then
            uncommitted_parts="\033[32m+${insertions}\033[0m"
        fi
        if [ "$deletions" -gt 0 ]; then
            if [ -n "$uncommitted_parts" ]; then
                uncommitted_parts="${uncommitted_parts}\033[31m-${deletions}\033[0m"
            else
                uncommitted_parts="\033[31m-${deletions}\033[0m"
            fi
        fi
        uncommitted_lines="$uncommitted_parts"
    fi
fi

# Get context remaining percentage
context_pct=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty' 2>/dev/null)

# Get token usage from context_window
tokens_info=""
total_input=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0' 2>/dev/null)
total_output=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0' 2>/dev/null)

# Format token counts in K (thousands) for readability
if [ "$total_input" -gt 0 ] || [ "$total_output" -gt 0 ]; then
    # Convert to K format (e.g., 15234 -> 15.2K)
    input_k=$(awk "BEGIN {printf \"%.1f\", $total_input/1000}")
    output_k=$(awk "BEGIN {printf \"%.1f\", $total_output/1000}")
    tokens_info="${input_k}K↓ ${output_k}K↑"
fi

# Get cost from Claude Code's actual data structure
cost_info=""
total_cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0' 2>/dev/null)
session_id=$(echo "$input" | jq -r '.session_id // ""' 2>/dev/null)

if (( $(echo "$total_cost > 0" | bc -l 2>/dev/null) )); then
    # Track cost history for 7-day rolling total
    cost_log="$HOME/.claude/cost-history.log"
    current_date=$(date +%Y-%m-%d)
    cutoff_date=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d 2>/dev/null)

    # Update current session cost
    if [ -n "$session_id" ]; then
        # Remove old entry for this session if exists, then add new
        grep -v "^$session_id|" "$cost_log" 2>/dev/null > "${cost_log}.tmp" || touch "${cost_log}.tmp"
        echo "$session_id|$current_date|$total_cost" >> "${cost_log}.tmp"
        mv "${cost_log}.tmp" "$cost_log"
    fi

    # Calculate 7-day total (sum costs for entries >= cutoff date)
    weekly_cost=$(awk -F'|' -v cutoff="$cutoff_date" '$2 >= cutoff {sum += $3} END {printf "%.2f", sum}' "$cost_log" 2>/dev/null || echo "0")

    # Clean up entries older than 7 days
    awk -F'|' -v cutoff="$cutoff_date" '$2 >= cutoff' "$cost_log" > "${cost_log}.tmp" 2>/dev/null && mv "${cost_log}.tmp" "$cost_log"

    # Format: $5.01 (7d:$23.45)
    cost_info="\$$(printf "%.2f" "$total_cost") (7d:\$$(printf "%.2f" "$weekly_cost"))"
fi

# Build the status line with embedded colors
# Color scheme (matching zsh PROMPT):
# - Path: cyan (36m) - directory location
# - Branch: green (32m) - git branch (matches shell PS1)
# - Line changes: green/red (32m/31m) - +additions/-deletions
# - Tokens: magenta (35m) - token usage
# - Cost: magenta (35m) - cost metrics
# - Model: blue (34m) - which model is active

status_line="\033[36m${cwd}\033[0m"
if [ -n "$git_info" ]; then
    status_line="${status_line}\033[32m${git_info}\033[0m"
fi
if [ -n "$uncommitted_lines" ]; then
    status_line="${status_line} ${uncommitted_lines}"
fi
if [ -n "$tokens_info" ]; then
    status_line="${status_line} \033[35m${tokens_info}\033[0m"
fi
if [ -n "$cost_info" ]; then
    status_line="${status_line} \033[35m${cost_info}\033[0m"
fi
if [ -n "$context_pct" ]; then
    # Color code based on remaining: green >50%, yellow 20-50%, red <20%
    pct_num=$(printf "%.0f" "$context_pct" 2>/dev/null || echo "0")
    if [ "$pct_num" -le 20 ]; then
        ctx_color="31"  # red - low remaining
    elif [ "$pct_num" -le 50 ]; then
        ctx_color="33"  # yellow - medium remaining
    else
        ctx_color="32"  # green - high remaining
    fi
    status_line="${status_line} \033[${ctx_color}m${pct_num}% left\033[0m"
fi
status_line="${status_line} \033[34m[${model_short}]\033[0m"

# Print with -e to interpret escape sequences
printf "%b" "$status_line"