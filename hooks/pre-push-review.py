#!/usr/bin/env python3
"""
PreToolUse hook (Bash): Advisory review before git push.

When a Bash command contains 'git push', checks unpushed commits for
security-sensitive file changes and suggests running the
defensive-design-reviewer agent before pushing.

This hook ADVISES but does NOT BLOCK. It always exits 0.

Exit codes:
    0 = Allow (always)

Output:
    JSON on stdout with hookSpecificOutput.additionalContext when
    security-sensitive files are detected in unpushed commits.
    Silent (no output) when no sensitive files found.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

# File path patterns that suggest security/architecture-sensitive changes.
# Matched against the filename (basename), case-insensitive.
SECURITY_SENSITIVE_PATTERNS = re.compile(
    r"(?:auth|login|session|token|permission|rbac|acl|middleware|guard|"
    r"policy|password|credential|oauth|saml|jwt|crypto|encrypt|decrypt|"
    r"hash|secret|security|cors|csrf|sanitiz|upload|webhook|callback|"
    r"redirect|proxy|gateway|rate.?limit|admin|privilege|role|"
    r"migration|docker|k8s|kubernetes|terraform|cloudformation|"
    r"iam|firewall|nginx|apache|envoy|config)\.",
    re.IGNORECASE,
)

# Directory patterns that suggest infrastructure or security concern
SECURITY_SENSITIVE_DIRS = re.compile(
    r"(?:^|/)(?:auth|security|middleware|guards|policies|permissions|"
    r"infra|infrastructure|deploy|k8s|terraform|docker|ci|\.github/workflows)/",
    re.IGNORECASE,
)


def get_unpushed_files() -> list[str]:
    """Get list of files changed in unpushed commits."""
    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:", "@{upstream}..HEAD"],
            capture_output=True, text=True, check=True,
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except subprocess.CalledProcessError:
        # No upstream or git error — no files to check
        return []


def find_sensitive_files(files: list[str]) -> list[str]:
    """Filter files to those matching security-sensitive patterns."""
    sensitive = []
    seen = set()
    for filepath in files:
        if filepath in seen:
            continue
        seen.add(filepath)

        basename = filepath.rsplit("/", 1)[-1] if "/" in filepath else filepath

        if SECURITY_SENSITIVE_PATTERNS.search(basename):
            sensitive.append(filepath)
        elif SECURITY_SENSITIVE_DIRS.search(filepath):
            sensitive.append(filepath)

    return sensitive


def main() -> None:
    # Parse hook input
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check git push commands
    if not re.search(r"\bgit\s+push\b", command):
        sys.exit(0)

    # Find security-sensitive files in unpushed commits
    unpushed_files = get_unpushed_files()
    if not unpushed_files:
        sys.exit(0)

    sensitive_files = find_sensitive_files(unpushed_files)
    if not sensitive_files:
        sys.exit(0)

    # Build advisory message
    file_list = "\n".join(f"  - {f}" for f in sensitive_files[:10])
    truncated = f"\n  ... and {len(sensitive_files) - 10} more" if len(sensitive_files) > 10 else ""

    message = (
        f"SECURITY-SENSITIVE FILES IN UNPUSHED COMMITS:\n"
        f"{file_list}{truncated}\n\n"
        f"Consider running the defensive-design-reviewer agent before pushing "
        f"to review fail-open/fail-closed decisions, trust boundaries, and "
        f"blast radius."
    )

    # Output advisory (does not block)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
