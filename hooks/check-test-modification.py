#!/usr/bin/env python3
"""
PreToolUse hook: Block test file modifications that are solely to make failing tests pass.

Policy: Tests must stay in sync with code, but Claude must NEVER auto-fix tests
just to make them pass. These cases MUST be raised to the human operator.

Exit codes:
  0 = Allow the change
  2 = Block with error message (stderr shown to Claude)
"""
import json
import sys
import re
from pathlib import Path


def is_test_file(file_path: str) -> bool:
    """Check if this is a test file."""
    path = Path(file_path)
    name = path.name

    # Match test file patterns
    patterns = [
        r'^test_.*\.py$',      # test_*.py
        r'.*_test\.py$',       # *_test.py
        r'^tests?\.py$',       # test.py or tests.py
    ]

    # Also check if it's in a tests directory
    in_tests_dir = 'tests' in path.parts or 'test' in path.parts

    return any(re.match(p, name) for p in patterns) or in_tests_dir


def detect_assertion_only_changes(old_content: str, new_content: str) -> list:
    """
    Detect changes that only modify assertion expected values.
    Returns list of suspicious changes.
    """
    if not old_content:
        return []

    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    suspicious_changes = []

    # Compare line by line (simple diff)
    max_lines = max(len(old_lines), len(new_lines))

    for i in range(max_lines):
        old_line = old_lines[i] if i < len(old_lines) else ''
        new_line = new_lines[i] if i < len(new_lines) else ''

        if old_line == new_line:
            continue

        # Check for assertion value changes
        # Pattern: assert X == OLD_VALUE -> assert X == NEW_VALUE
        old_assert = re.search(r'assert\s+(.+?)\s*==\s*(.+?)(?:\s*#.*)?$', old_line.strip())
        new_assert = re.search(r'assert\s+(.+?)\s*==\s*(.+?)(?:\s*#.*)?$', new_line.strip())

        if old_assert and new_assert:
            # Same expression being asserted, different expected value
            if old_assert.group(1).strip() == new_assert.group(1).strip():
                if old_assert.group(2).strip() != new_assert.group(2).strip():
                    suspicious_changes.append({
                        'line': i + 1,
                        'old': old_line.strip(),
                        'new': new_line.strip(),
                        'type': 'assertion_value_change'
                    })

        # Check for assertEqual/assertEquals changes
        old_eq = re.search(r'self\.assert(Equal|Equals?)\s*\(\s*(.+?)\s*,\s*(.+?)\s*\)', old_line)
        new_eq = re.search(r'self\.assert(Equal|Equals?)\s*\(\s*(.+?)\s*,\s*(.+?)\s*\)', new_line)

        if old_eq and new_eq:
            if old_eq.group(2).strip() == new_eq.group(2).strip():
                if old_eq.group(3).strip() != new_eq.group(3).strip():
                    suspicious_changes.append({
                        'line': i + 1,
                        'old': old_line.strip(),
                        'new': new_line.strip(),
                        'type': 'assertEqual_value_change'
                    })

        # Check for pytest.approx changes
        old_approx = re.search(r'==\s*pytest\.approx\s*\(\s*(.+?)\s*\)', old_line)
        new_approx = re.search(r'==\s*pytest\.approx\s*\(\s*(.+?)\s*\)', new_line)

        if old_approx and new_approx:
            if old_approx.group(1).strip() != new_approx.group(1).strip():
                suspicious_changes.append({
                    'line': i + 1,
                    'old': old_line.strip(),
                    'new': new_line.strip(),
                    'type': 'approx_value_change'
                })

    return suspicious_changes


def detect_test_removal(old_content: str, new_content: str) -> list:
    """Detect if test functions/methods are being removed."""
    removed_tests = []

    if not old_content:
        return []

    # Find all test functions in old content
    old_tests = set(re.findall(r'def\s+(test_\w+)\s*\(', old_content))
    new_tests = set(re.findall(r'def\s+(test_\w+)\s*\(', new_content))

    removed = old_tests - new_tests
    for test_name in removed:
        removed_tests.append({
            'test_name': test_name,
            'type': 'test_removal'
        })

    return removed_tests


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No input or invalid JSON - allow by default
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    # Only check Edit and Write operations
    if tool_name not in ('Edit', 'Write'):
        sys.exit(0)

    file_path = tool_input.get('file_path', '')

    # Only care about test files
    if not is_test_file(file_path):
        sys.exit(0)

    # Get the new content
    if tool_name == 'Write':
        new_content = tool_input.get('content', '')
    elif tool_name == 'Edit':
        new_content = tool_input.get('new_string', '')
    else:
        sys.exit(0)

    # Read existing content
    try:
        with open(file_path, 'r') as f:
            old_content = f.read()
    except FileNotFoundError:
        # New file - allow creation
        sys.exit(0)

    # For Edit operations, we need to simulate the change
    if tool_name == 'Edit':
        old_string = tool_input.get('old_string', '')
        new_string = tool_input.get('new_string', '')
        # Simulate the edit
        if old_string in old_content:
            simulated_new = old_content.replace(old_string, new_string, 1)
        else:
            simulated_new = old_content

        # Check just the changed portion for suspicious patterns
        suspicious = detect_assertion_only_changes(old_string, new_string)
    else:
        # Full file write
        suspicious = detect_assertion_only_changes(old_content, new_content)
        suspicious.extend(detect_test_removal(old_content, new_content))

    if suspicious:
        error_lines = [
            "",
            "=" * 70,
            "POLICY VIOLATION: Suspected test auto-fix detected",
            "=" * 70,
            "",
            f"File: {file_path}",
            "",
            "Claude Code policy PROHIBITS modifying tests solely to make them pass.",
            "This must be escalated to the human operator for review.",
            "",
            "Detected suspicious changes:",
            ""
        ]

        for change in suspicious:
            if change['type'] in ('assertion_value_change', 'assertEqual_value_change', 'approx_value_change'):
                error_lines.extend([
                    f"  Line {change['line']}: Assertion value changed",
                    f"    OLD: {change['old']}",
                    f"    NEW: {change['new']}",
                    ""
                ])
            elif change['type'] == 'test_removal':
                error_lines.extend([
                    f"  Test function removed: {change['test_name']}",
                    ""
                ])

        error_lines.extend([
            "-" * 70,
            "REQUIRED ACTION:",
            "",
            "Do NOT modify tests to match code behavior. Instead:",
            "",
            "1. STOP and inform the operator that tests are failing",
            "2. Explain WHAT tests are failing and WHY",
            "3. Ask the operator to decide:",
            "   - Are the code changes correct (tests need legitimate update)?",
            "   - Did the code changes introduce a bug (code should be fixed)?",
            "",
            "The operator must make this decision, not Claude.",
            "=" * 70,
            ""
        ])

        print('\n'.join(error_lines), file=sys.stderr)
        sys.exit(2)

    # No suspicious changes detected
    sys.exit(0)


if __name__ == '__main__':
    main()
