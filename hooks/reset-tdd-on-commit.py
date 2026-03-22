#!/usr/bin/env python3
"""
PreToolUse hook (Bash): Reset TDD enforcement after git commit.

When a Bash command contains 'git commit', deletes the session's
TDD-satisfied marker so that the next source file edit requires
a test to be written first.

Exit codes:
  0 = Always allow (this hook never blocks)
"""
import json
import os
import re
import sys
import tempfile

CACHE_DIR = os.path.join(tempfile.gettempdir(), 'claude-tdd-cache')


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    command = tool_input.get('command', '')

    if not re.search(r'\bgit\s+commit\b', command):
        sys.exit(0)

    session_id = input_data.get('session_id', '')
    if not session_id:
        sys.exit(0)

    marker = os.path.join(CACHE_DIR, f'{session_id}.satisfied')
    try:
        os.remove(marker)
    except FileNotFoundError:
        pass

    sys.exit(0)


if __name__ == '__main__':
    main()
