#!/usr/bin/env python3
"""
PreToolUse hook (Bash): Enforce atomic commits.

When a Bash command contains 'git commit', analyzes the staged changes
and commit message for signs of non-atomic commits (multiple unrelated
topics in a single commit).

Exit codes:
  0 = Allow the commit
  2 = Block with error message (stderr shown to Claude)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Conventional commit prefixes
CONVENTIONAL_PREFIXES = {
    'feat', 'fix', 'chore', 'refactor', 'test', 'docs', 'style',
    'perf', 'ci', 'build', 'revert',
}

# Commit messages containing these words suggest intentionally cross-cutting changes
CROSS_CUTTING_KEYWORDS = {
    'rename', 'refactor', 'move', 'migrate', 'reorganize', 'restructure',
    'update dependencies', 'bump', 'format', 'lint', 'initial commit',
}

# Directories that are inherently cross-cutting (changes here don't count as separate topics)
CROSS_CUTTING_DIRS = {
    '.claude', '.github', '.vscode', '.idea', 'node_modules',
    '__pycache__', '.git',
}

# Minimum number of distinct directory groups to trigger a warning
MIN_DIR_GROUPS_FOR_WARNING = 3

CACHE_DIR = os.path.join(tempfile.gettempdir(), 'claude-atomic-cache')


def get_staged_files() -> list[str]:
    """Get list of files staged for commit."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True, text=True, check=True,
        )
        return [f for f in result.stdout.strip().split('\n') if f]
    except subprocess.CalledProcessError:
        return []


def extract_commit_message(command: str) -> str | None:
    """Extract the commit message from a git commit command."""
    # Match -m "message" or -m 'message'
    match = re.search(r'-m\s+["\'](.+?)["\']', command)
    if match:
        return match.group(1)

    # Match -m "$(cat <<'EOF' ... EOF )"  (heredoc pattern)
    match = re.search(r'-m\s+"\$\(cat\s+<<[\'"]?EOF[\'"]?\s*\n(.*?)\n\s*EOF', command, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def group_files_by_directory(files: list[str]) -> dict[str, list[str]]:
    """Group files by their top-level directory (or root for top-level files)."""
    groups: dict[str, list[str]] = {}
    for filepath in files:
        parts = Path(filepath).parts
        if len(parts) <= 1:
            group = '(root)'
        else:
            group = parts[0]

        # Skip cross-cutting directories
        if group in CROSS_CUTTING_DIRS:
            continue

        if group not in groups:
            groups[group] = []
        groups[group].append(filepath)

    return groups


def has_multiple_conventional_prefixes(message: str) -> bool:
    """Check if the commit message contains multiple conventional commit prefixes."""
    # Look for patterns like "feat: ... and fix: ..." or multiple prefix: patterns
    found_prefixes = set()
    for prefix in CONVENTIONAL_PREFIXES:
        if re.search(rf'\b{prefix}[:(]', message, re.IGNORECASE):
            found_prefixes.add(prefix)
    return len(found_prefixes) > 1


def message_has_multiple_topics(message: str) -> list[str]:
    """Check if the commit message suggests multiple unrelated topics.

    Returns a list of reasons if suspicious, empty list if clean.
    """
    reasons = []

    # Check for multiple conventional commit prefixes
    if has_multiple_conventional_prefixes(message):
        reasons.append('Commit message contains multiple conventional commit prefixes')

    # Check for " and " connecting what look like separate changes
    # Exclude common false positives like "search and replace", "read and write"
    false_positive_patterns = [
        r'search and replace',
        r'read and write',
        r'trial and error',
        r'back and forth',
        r'pros and cons',
        r'request and response',
        r'input and output',
        r'start and stop',
        r'open and close',
        r'create and delete',
        r'add and remove',
    ]

    # Strip the conventional commit prefix before checking for " and "
    stripped = re.sub(r'^[a-z]+(\([^)]*\))?:\s*', '', message, flags=re.IGNORECASE)

    if ' and ' in stripped.lower():
        is_false_positive = any(
            re.search(pattern, stripped, re.IGNORECASE)
            for pattern in false_positive_patterns
        )
        if not is_false_positive:
            # Check if " and " connects verb phrases (suggesting two actions)
            and_match = re.search(r'(\b\w+)\s+and\s+(\b\w+)', stripped, re.IGNORECASE)
            if and_match:
                before_and = stripped[:and_match.start()].strip()
                after_and = stripped[and_match.end():].strip()
                # If both sides have enough substance, flag it
                if len(before_and.split()) >= 2 and len(after_and.split()) >= 2:
                    reasons.append(f'Commit message may describe multiple changes: "...{and_match.group()}..."')

    return reasons


def is_cross_cutting_message(message: str) -> bool:
    """Check if the commit message indicates an intentionally cross-cutting change."""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in CROSS_CUTTING_KEYWORDS)


def is_merge_commit(command: str) -> bool:
    """Check if this is a merge commit."""
    return '--no-edit' in command or 'merge' in command.lower()


def check_bypass(input_data: dict) -> bool:
    """Check if the user has said 'single commit' or 'one commit' in the transcript."""
    transcript_path = input_data.get('transcript_path', '')
    if not transcript_path:
        return False

    session_id = input_data.get('session_id', '')
    if session_id:
        os.makedirs(CACHE_DIR, exist_ok=True)
        marker = os.path.join(CACHE_DIR, f'{session_id}.atomic-bypass')
        if os.path.exists(marker):
            return True

    bypass_pattern = re.compile(r'single\s+commit|one\s+commit|skip\s+atomicity', re.IGNORECASE)

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entry.get('type') != 'user':
                    continue

                content_blocks = entry.get('message', {}).get('content', [])
                if not isinstance(content_blocks, list):
                    continue

                for block in content_blocks:
                    text = ''
                    if isinstance(block, dict):
                        text = block.get('text', '')
                    elif isinstance(block, str):
                        text = block

                    if text and bypass_pattern.search(text):
                        # Cache the bypass
                        if session_id:
                            with open(marker, 'w') as mf:
                                mf.write('')
                        return True
    except (FileNotFoundError, PermissionError):
        pass

    return False


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    command = tool_input.get('command', '')

    # Only check git commit commands
    if not re.search(r'\bgit\s+commit\b', command):
        sys.exit(0)

    # Skip merge commits
    if is_merge_commit(command):
        sys.exit(0)

    # Check for user bypass
    if check_bypass(input_data):
        sys.exit(0)

    # Get staged files and commit message
    staged_files = get_staged_files()
    if not staged_files:
        sys.exit(0)

    commit_message = extract_commit_message(command) or ''

    # Skip cross-cutting changes
    if is_cross_cutting_message(commit_message):
        sys.exit(0)

    problems = []

    # Check 1: Commit message suggests multiple topics
    message_issues = message_has_multiple_topics(commit_message)
    problems.extend(message_issues)

    # Check 2: Files span too many unrelated directories
    file_groups = group_files_by_directory(staged_files)
    if len(file_groups) >= MIN_DIR_GROUPS_FOR_WARNING:
        group_summary = []
        for group, files in sorted(file_groups.items()):
            group_summary.append(f'  - {group}/: {len(files)} file(s)')
        problems.append(
            'Staged files span multiple directories:\n' + '\n'.join(group_summary)
        )

    if not problems:
        sys.exit(0)

    # Block the commit
    error_lines = [
        '',
        '=' * 70,
        'ATOMIC COMMIT POLICY: One topic per commit',
        '=' * 70,
        '',
        'This commit appears to mix multiple topics:',
        '',
    ]

    for problem in problems:
        for line in problem.split('\n'):
            error_lines.append(f'  {line}')
        error_lines.append('')

    error_lines.extend([
        'Consider splitting into separate, focused commits.',
        '',
        'If this is intentionally a single change, ask the user to',
        'say "single commit" and then retry.',
        '=' * 70,
        '',
    ])

    print('\n'.join(error_lines), file=sys.stderr)
    sys.exit(2)


if __name__ == '__main__':
    main()
