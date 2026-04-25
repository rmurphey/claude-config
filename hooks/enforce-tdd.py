#!/usr/bin/env python3
"""
PreToolUse hook: Enforce TDD for all non-documentation changes.

Before allowing edits to source files, checks the session transcript
to verify that a test file has already been created or modified.
If no test file has been touched yet, blocks the edit.

Exit codes:
  0 = Allow the change
  2 = Block with error message (stderr shown to Claude)
"""
import json
import os
import sys
import re
import tempfile
from pathlib import Path

CACHE_DIR = os.path.join(tempfile.gettempdir(), 'claude-tdd-cache')

# File extensions considered documentation or config (exempt from TDD)
DOC_CONFIG_EXTENSIONS = {
    '.md', '.rst', '.txt', '.adoc',
    '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini', '.env',
    '.lock', '.gitignore', '.dockerignore',
    '.csv', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico',
    '.html', '.css',  # markup/styles typically not TDD'd
    '.sh', '.bash', '.zsh',  # shell scripts
    '.dockerfile',
}

# Files that are always exempt (by name)
EXEMPT_FILENAMES = {
    'Makefile', 'Dockerfile', 'Procfile', 'Gemfile',
    '.gitignore', '.dockerignore', '.eslintrc', '.prettierrc',
    'package.json', 'package-lock.json', 'tsconfig.json',
    'pyproject.toml', 'setup.cfg', 'setup.py',
    'requirements.txt', 'Pipfile', 'Pipfile.lock',
    'CLAUDE.md', 'README.md', 'CHANGELOG.md', 'LICENSE',
}

# Directories that are always exempt
EXEMPT_DIRS = {
    '.claude', '.github', '.vscode', '.idea',
    'node_modules', '__pycache__', '.git',
    'docs', 'doc', 'documentation',
}


def is_test_file(file_path: str) -> bool:
    """Check if this is a test file."""
    path = Path(file_path)
    name = path.name
    parts = path.parts

    # Directory-based detection
    if any(d in parts for d in ('tests', 'test', '__tests__', 'spec', 'specs')):
        return True

    # Name-based detection
    test_patterns = [
        r'^test_.*\.py$',
        r'.*_test\.py$',
        r'^tests?\.py$',
        r'.*\.test\.[jt]sx?$',
        r'.*\.spec\.[jt]sx?$',
        r'.*_test\.go$',
        r'.*_test\.rs$',
        r'.*Test\.java$',
    ]
    return any(re.match(p, name) for p in test_patterns)


def is_exempt(file_path: str) -> bool:
    """Check if this file is exempt from TDD requirement."""
    path = Path(file_path)

    # Exempt by filename
    if path.name in EXEMPT_FILENAMES:
        return True

    # Exempt by extension
    if path.suffix.lower() in DOC_CONFIG_EXTENSIONS:
        return True

    # Exempt by directory
    if any(d in path.parts for d in EXEMPT_DIRS):
        return True

    return False


def scan_transcript(transcript_path: str) -> dict:
    """Scan the transcript for test edits and TDD bypass requests.

    Returns dict with:
      - has_test_edit: bool — whether a test file was edited/written
      - has_tdd_bypass: bool — whether the user said to skip TDD
    """
    result = {'has_test_edit': False, 'has_tdd_bypass': False}
    bypass_pattern = re.compile(r'skip\s+tdd', re.IGNORECASE)

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get('type', '')
                message = entry.get('message', {})
                content = message.get('content', [])

                # Check for test file edits in assistant messages (always list-shaped).
                if entry_type == 'assistant' and isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get('type') == 'tool_use' and block.get('name') in ('Edit', 'Write'):
                            edited_path = block.get('input', {}).get('file_path', '')
                            if is_test_file(edited_path):
                                result['has_test_edit'] = True

                # Check for user bypass request. User-message content can be a plain
                # string (typed message) OR a list of blocks (tool results, etc.).
                if entry_type == 'user':
                    if isinstance(content, str):
                        if bypass_pattern.search(content):
                            result['has_tdd_bypass'] = True
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                text = block.get('text', '')
                                if text and bypass_pattern.search(text):
                                    result['has_tdd_bypass'] = True
                            elif isinstance(block, str) and bypass_pattern.search(block):
                                result['has_tdd_bypass'] = True

                # Early exit if both found
                if result['has_test_edit'] and result['has_tdd_bypass']:
                    return result
    except (FileNotFoundError, PermissionError):
        # If we can't read transcript, don't block
        result['has_test_edit'] = True

    return result


def tests_exist_for_file(file_path: str) -> bool:
    """Check if test files already exist that correspond to the given source file."""
    path = Path(file_path).resolve()
    stem = path.stem
    suffix = path.suffix

    if suffix == '.py':
        candidates = [f'test_{stem}.py', f'{stem}_test.py']
    elif suffix in ('.ts', '.tsx', '.js', '.jsx'):
        candidates = [f'{stem}.test{suffix}', f'{stem}.spec{suffix}']
        for ext in ('.ts', '.tsx', '.js', '.jsx'):
            if ext != suffix:
                candidates += [f'{stem}.test{ext}', f'{stem}.spec{ext}']
    elif suffix == '.go':
        candidates = [f'{stem}_test.go']
    elif suffix == '.rs':
        candidates = [f'{stem}_test.rs']
    elif suffix == '.java':
        candidates = [f'{stem}Test.java']
    else:
        candidates = [f'test_{stem}{suffix}', f'{stem}_test{suffix}']

    search_dirs = [
        path.parent,
        path.parent / 'tests',
        path.parent / 'test',
        path.parent / '__tests__',
    ]
    grandparent = path.parent.parent
    if grandparent != path.parent:
        search_dirs += [grandparent / 'tests', grandparent / 'test']

    for directory in search_dirs:
        for candidate in candidates:
            if (directory / candidate).exists():
                return True

    return False


def cache_path_for_session(session_id: str) -> str:
    """Return the path to this session's TDD-satisfied marker file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f'{session_id}.satisfied')


def is_tdd_satisfied(session_id: str) -> bool:
    """Check if TDD was already satisfied for this session."""
    return os.path.exists(cache_path_for_session(session_id))


def mark_tdd_satisfied(session_id: str) -> None:
    """Write a marker so future calls in this session skip the transcript scan."""
    with open(cache_path_for_session(session_id), 'w') as f:
        f.write('')


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    if tool_name not in ('Edit', 'Write'):
        sys.exit(0)

    file_path = tool_input.get('file_path', '')

    # Don't enforce TDD for test files themselves or exempt files
    if is_test_file(file_path) or is_exempt(file_path):
        sys.exit(0)

    session_id = input_data.get('session_id', '')

    # Fast path: already satisfied for this session
    if session_id and is_tdd_satisfied(session_id):
        sys.exit(0)

    # Check transcript for prior test edits or bypass
    transcript_path = input_data.get('transcript_path', '')
    if not transcript_path:
        sys.exit(0)

    transcript_state = scan_transcript(transcript_path)

    if transcript_state['has_test_edit'] or transcript_state['has_tdd_bypass'] or tests_exist_for_file(file_path):
        if session_id:
            mark_tdd_satisfied(session_id)
        sys.exit(0)

    # No test file has been edited yet, no bypass, and no existing tests found — block
    error_lines = [
        "",
        "=" * 70,
        "TDD POLICY: Write a failing test first",
        "=" * 70,
        "",
        f"You are trying to edit: {file_path}",
        "",
        "No test file has been created or modified yet in this session.",
        "Per project policy, all non-documentation changes require TDD:",
        "",
        "  1. Write a failing test that describes the expected behavior",
        "  2. Run the test to confirm it fails",
        "  3. Then implement the change to make the test pass",
        "",
        "Please write the test first, then retry this edit.",
        "",
        "If the user has explicitly asked to skip TDD for this change,",
        "ask them to say 'skip TDD' and then retry.",
        "=" * 70,
        "",
    ]

    print('\n'.join(error_lines), file=sys.stderr)
    sys.exit(2)


if __name__ == '__main__':
    main()
