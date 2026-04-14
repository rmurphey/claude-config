#!/usr/bin/env python3
"""
PreToolUse hook (Bash): Advisory review before Python script execution.

When a Bash command runs a Python script (python3/python <file>), reads
the script and flags dangerous patterns before execution.

This hook ADVISES but does NOT BLOCK. It always exits 0.

Exit codes:
    0 = Allow (always)

Output:
    JSON on stdout with hookSpecificOutput.additionalContext when
    dangerous patterns are detected. Silent when script looks safe.
"""
from __future__ import annotations

import json
import os
import re
import sys

# Patterns that extract the script path from a python command
PYTHON_CMD_PATTERN = re.compile(
    r"\b(?:python3?|python3\.\d+)\s+"
    r"(?!-[cm])"  # not python -c or python -m
    r"([^\s;|&><]+\.py)\b"
)

# Dangerous patterns to flag in Python scripts.
# (label, pattern, description)
DANGEROUS_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "EVAL/EXEC",
        re.compile(r"\beval\s*\(|\bexec\s*\("),
        "eval() or exec() can execute arbitrary code",
    ),
    (
        "PICKLE_LOAD",
        re.compile(r"\bpickle\.loads?\(|\bcPickle\.loads?\("),
        "pickle.load() executes arbitrary code during deserialization",
    ),
    (
        "YAML_UNSAFE",
        re.compile(r"\byaml\.load\s*\([^)]*(?!Loader)"),
        "yaml.load() without SafeLoader executes arbitrary code",
    ),
    (
        "SHELL_INJECTION",
        re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
        "subprocess with shell=True is vulnerable to command injection",
    ),
    (
        "OS_SYSTEM",
        re.compile(r"\bos\.system\s*\("),
        "os.system() runs commands through the shell — use subprocess.run()",
    ),
    (
        "TEMP_MKTEMP",
        re.compile(r"\btempfile\.mktemp\s*\("),
        "tempfile.mktemp() has a race condition — use mkstemp() or NamedTemporaryFile()",
    ),
    (
        "REQUESTS_NO_VERIFY",
        re.compile(r"verify\s*=\s*False"),
        "Disabling TLS verification allows man-in-the-middle attacks",
    ),
    (
        "HARDCODED_SECRET",
        re.compile(
            r"""(?:password|secret|token|api_key|apikey)\s*=\s*['"][^'"]{8,}['"]""",
            re.IGNORECASE,
        ),
        "Hardcoded secret — use environment variables or a secret manager",
    ),
    (
        "CHMOD_777",
        re.compile(r"os\.chmod\s*\([^)]*0o?777"),
        "chmod 777 grants all permissions — use the minimum required",
    ),
    (
        "RM_RF",
        re.compile(r"shutil\.rmtree\s*\(|os\.removedirs\s*\("),
        "Recursive delete — verify the path is safe before execution",
    ),
]

# Maximum file size to scan (skip very large files)
MAX_FILE_SIZE = 500_000  # 500KB


def extract_script_path(command: str) -> str | None:
    """Extract the Python script path from a bash command."""
    match = PYTHON_CMD_PATTERN.search(command)
    if match:
        return match.group(1)
    return None


def scan_script(filepath: str) -> list[tuple[int, str, str]]:
    """Scan a Python script for dangerous patterns.

    Returns list of (line_number, label, description).
    """
    findings: list[tuple[int, str, str]] = []

    try:
        size = os.path.getsize(filepath)
        if size > MAX_FILE_SIZE:
            return findings

        with open(filepath, encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                for label, pattern, description in DANGEROUS_PATTERNS:
                    if pattern.search(line):
                        findings.append((line_num, label, description))
                        break  # one finding per line
    except OSError:
        pass

    return findings


def main() -> None:
    # Parse hook input
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check commands that run Python scripts
    script_path = extract_script_path(command)
    if not script_path:
        sys.exit(0)

    # Resolve the script path
    if not os.path.isabs(script_path):
        # Try relative to cwd
        if not os.path.isfile(script_path):
            sys.exit(0)

    if not os.path.isfile(script_path):
        sys.exit(0)

    # Scan the script
    findings = scan_script(script_path)
    if not findings:
        sys.exit(0)

    # Build advisory message
    finding_lines = []
    for line_num, label, description in findings[:10]:
        finding_lines.append(f"  Line {line_num}: [{label}] {description}")

    truncated = ""
    if len(findings) > 10:
        truncated = f"\n  ... and {len(findings) - 10} more"

    message = (
        f"PYTHON SCRIPT PRE-EXECUTION REVIEW: {script_path}\n"
        f"Found {len(findings)} potential issue(s):\n"
        + "\n".join(finding_lines)
        + truncated
        + "\n\nReview these patterns before running the script."
    )

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
