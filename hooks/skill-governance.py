#!/usr/bin/env python3
"""
PreToolUse hook: Governance for skill and agent execution.

Inspects Bash commands that invoke skills/agents from ~/.claude/skills/
or ~/.claude/agents/. Enforces blocklist, dangerous pattern detection,
and optional audit logging.

Design principle: FAIL CLOSED. If the hook can't parse input, read config,
or determine safety, it blocks and explains why. Silent passthrough only
happens for commands that are clearly not skill invocations.

Exit codes:
  0 = Allow the command
  2 = Block with error message (stderr shown to Claude)

Config (JSON):
  Location: SKILL_GOVERNANCE_CONFIG env var, or ~/.claude/skill-governance.json
  {
    "blocked": ["skill-name", ...],
    "audit": false,
    "audit_log": "~/.claude/skill-audit.log",
    "dangerous_patterns": ["extra-pattern", ...]
  }
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
DEFAULT_CONFIG_PATH = CLAUDE_DIR / "skill-governance.json"

SKILL_PATH_PATTERNS = [
    re.compile(r"~/.claude/(?:skills|agents)/"),
    re.compile(re.escape(str(CLAUDE_DIR / "skills")) + r"/"),
    re.compile(re.escape(str(CLAUDE_DIR / "agents")) + r"/"),
    re.compile(r"\$\{?HOME\}?/.claude/(?:skills|agents)/"),
]

SKILL_NAME_PATTERN = re.compile(
    r"(?:~/.claude|\$\{?HOME\}?/.claude|"
    + re.escape(str(CLAUDE_DIR))
    + r")/(?:skills|agents)/([a-zA-Z0-9_-]+)"
)

DEFAULT_DANGEROUS_PATTERNS = [
    r"\$\(",           # command substitution
    r"`",              # backtick substitution
    r"\|\s*bash\b",    # pipe to bash
    r"\|\s*sh\b",      # pipe to sh
    r"\|\s*zsh\b",     # pipe to zsh
    r"\|\s*curl\b",    # pipe to curl (exfiltration)
    r"\|\s*wget\b",    # pipe to wget (exfiltration)
    r"\|\s*nc\b",      # pipe to netcat (exfiltration)
    r"\beval[\s\"'(]",  # eval prefix (with or without space)
    r"\bsudo\s",       # sudo prefix
]


def block(message: str) -> None:
    """Block execution with an error message and exit."""
    print(message, file=sys.stderr)
    sys.exit(2)


def audit_log(config: dict, skill_name: str, command: str, decision: str, reason: str) -> None:
    """Append an entry to the audit log if auditing is enabled."""
    if not config.get("audit", False):
        return

    log_path = os.path.expanduser(
        config.get("audit_log", str(CLAUDE_DIR / "skill-audit.log"))
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = json.dumps({
        "timestamp": timestamp,
        "skill": skill_name,
        "command": command,
        "decision": decision,
        "reason": reason,
    })

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except OSError as e:
        block(
            f"SKILL GOVERNANCE: Audit log write failed: {e}\n"
            f"Cannot proceed without audit trail. Fix permissions on: {log_path}"
        )


def load_config() -> dict:
    """Load governance config. Fails closed on error for explicit config paths."""
    config_env = os.environ.get("SKILL_GOVERNANCE_CONFIG")
    config_path = os.path.expanduser(
        config_env if config_env is not None else str(DEFAULT_CONFIG_PATH)
    )

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if config_env is None:
            return {}  # default path absent is fine
        block(
            f"SKILL GOVERNANCE: Config file not found: {config_path}\n"
            f"The SKILL_GOVERNANCE_CONFIG env var points to a missing file.\n"
            f"Create the config file or unset the env var."
        )
    except json.JSONDecodeError as e:
        block(
            f"SKILL GOVERNANCE: Config file has invalid JSON: {config_path}\n"
            f"Parse error: {e}\n"
            f"Fix the config file before proceeding."
        )
    except OSError as e:
        block(
            f"SKILL GOVERNANCE: Cannot read config file: {config_path}\n"
            f"Error: {e}"
        )

    return {}  # unreachable, but satisfies type checker


def is_skill_invocation(command: str) -> bool:
    """Check if this command invokes a skill or agent."""
    return any(p.search(command) for p in SKILL_PATH_PATTERNS)


def extract_skill_names(command: str) -> list[str]:
    """Extract skill/agent names from a command."""
    return SKILL_NAME_PATTERN.findall(command)


def check_blocklist(skill_names: list[str], blocked: list[str]) -> str | None:
    """Check if any invoked skill is blocked. Returns blocked name or None."""
    blocked_set = set(blocked)
    for name in skill_names:
        if name in blocked_set:
            return name
    return None


def check_dangerous_patterns(command: str, extra_patterns: list[str]) -> str | None:
    """Check for dangerous patterns in command. Returns matched pattern or None."""
    all_patterns = DEFAULT_DANGEROUS_PATTERNS + extra_patterns
    for pattern in all_patterns:
        try:
            if re.search(pattern, command):
                return pattern
        except re.error as e:
            block(
                f"SKILL GOVERNANCE: Invalid regex in dangerous_patterns config: {pattern!r}\n"
                f"Error: {e}\n"
                f"Fix the pattern in your governance config."
            )
    return None


def main() -> None:
    # Parse input — fail closed on bad input
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as e:
        block(
            f"SKILL GOVERNANCE: Failed to parse hook input.\n"
            f"Parse error: {e}\n"
            f"This hook fails closed — cannot allow commands without valid input."
        )
        return

    tool_name = input_data.get("tool_name", "")

    # Only inspect Bash commands
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = input_data.get("tool_input")
    if tool_input is None:
        block(
            "SKILL GOVERNANCE: Bash tool_input is missing.\n"
            "Expected {\"tool_input\": {\"command\": \"...\"}} in hook input.\n"
            "This hook fails closed — cannot allow commands without valid input."
        )
        return

    command = tool_input.get("command")
    if command is None:
        block(
            "SKILL GOVERNANCE: Bash command is missing from tool_input.\n"
            "Expected {\"tool_input\": {\"command\": \"...\"}} in hook input.\n"
            "This hook fails closed — cannot allow commands without valid input."
        )
        return

    if not isinstance(command, str):
        block(
            "SKILL GOVERNANCE: Bash command is not a string.\n"
            "This hook fails closed — cannot allow commands without valid input."
        )
        return

    # Non-skill commands pass through — this hook has no opinion on them
    if not command or not is_skill_invocation(command):
        sys.exit(0)

    # --- From here on, we're governing a skill invocation ---

    config = load_config()
    skill_names = extract_skill_names(command)
    extra_patterns = config.get("dangerous_patterns", [])

    # Check blocklist
    blocked_skill = check_blocklist(skill_names, config.get("blocked", []))
    if blocked_skill:
        audit_log(config, blocked_skill, command, "blocked", f"skill '{blocked_skill}' is on the blocklist")
        block(
            f"SKILL GOVERNANCE: Blocked skill '{blocked_skill}'.\n"
            f"This skill is on the blocklist in your governance config.\n"
            f"To unblock, remove '{blocked_skill}' from the 'blocked' array in your config."
        )
        return

    # Check dangerous patterns
    dangerous_match = check_dangerous_patterns(command, extra_patterns)
    if dangerous_match:
        skill_label = skill_names[0] if skill_names else "unknown"
        audit_log(config, skill_label, command, "blocked:dangerous", f"matched dangerous pattern: {dangerous_match}")
        block(
            f"SKILL GOVERNANCE: Dangerous pattern detected in skill invocation.\n"
            f"Pattern matched: {dangerous_match}\n"
            f"Command: {command}\n"
            f"This looks like a shell injection or unsafe operation.\n"
            f"If this is intentional, run the skill command directly without the dangerous pattern."
        )
        return

    # All checks passed — allow
    skill_label = skill_names[0] if skill_names else "unknown"
    audit_log(config, skill_label, command, "allowed", "passed all governance checks")
    sys.exit(0)


if __name__ == "__main__":
    main()
