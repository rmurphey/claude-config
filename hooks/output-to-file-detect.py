#!/usr/bin/env python3
"""Stop hook: Enforce that substantive Claude output is written to a file.

Phase 1 skeleton: this file installs the hook plumbing — config loading,
audit logging, short-circuit guards — but does NOT yet run detection or
emit block decisions. When `enabled: true`, every invocation appends a
payload entry to the audit log and exits 0. Phase 2 adds transcript
scanning, the prose-threshold heuristic, override-token handling, and
escalation to `decision: "block"`.

Design principles (from ~/.claude/plans/output-to-file-enforcement.md):
  - State file fails closed (Phase 2).
  - Audit log fails open (this file): a logging failure must not wedge
    the user's session. Print a stderr warning and continue.
  - Unexpected exceptions fail closed (exit 2) to leave a paper trail.
  - `stop_hook_active: true` short-circuits unconditionally — otherwise
    a later `decision: "block"` would loop.

Exit codes:
  0 = Allow (Stop hook has no opinion this turn)
  2 = Fail closed (bad input, bad config, unhandled error)
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

CLAUDE_DIR = Path.home() / ".claude"
DEFAULT_CONFIG_PATH = CLAUDE_DIR / "output-to-file.json"
DEFAULT_AUDIT_LOG = CLAUDE_DIR / "logs" / "output-enforcement.log"


def block(message: str) -> NoReturn:
    """Fail closed with a message on stderr."""
    print(f"OUTPUT-TO-FILE: {message}", file=sys.stderr)
    sys.exit(2)


def load_config() -> dict[str, object]:
    """Load the enforcement config. Fails closed when an explicit path is bad.

    If no OUTPUT_TO_FILE_CONFIG env var is set and the default config does
    not exist, returns {} — the hook treats this as disabled and exits 0.
    """
    config_env = os.environ.get("OUTPUT_TO_FILE_CONFIG")
    explicit = config_env is not None
    config_path = os.path.expanduser(config_env or str(DEFAULT_CONFIG_PATH))

    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if not explicit:
            return {}
        block(
            f"Config file not found: {config_path}\n"
            f"OUTPUT_TO_FILE_CONFIG points to a missing file."
        )
    except json.JSONDecodeError as e:
        block(f"Config file has invalid JSON: {config_path}\nParse error: {e}")
    except OSError as e:
        block(f"Cannot read config file: {config_path}\nError: {e}")


def audit_log(config: dict[str, object], payload: dict[str, object]) -> None:
    """Append a JSON line to the audit log. Fails open on any error.

    A disk-full or permissions failure must not break the user's session —
    enforcement still runs; only logging is lost. Warn on stderr so the
    failure is visible, but do not exit non-zero.
    """
    log_path_raw = config.get("audit_log", str(DEFAULT_AUDIT_LOG))
    if not isinstance(log_path_raw, str):
        log_path_raw = str(DEFAULT_AUDIT_LOG)
    log_path = Path(os.path.expanduser(log_path_raw))

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": 1,
        "session_id": payload.get("session_id"),
        "transcript_path": payload.get("transcript_path"),
        "stop_hook_active": payload.get("stop_hook_active", False),
    }

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        print(
            f"OUTPUT-TO-FILE: audit log write failed ({e}); continuing without logging.",
            file=sys.stderr,
        )


def run() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as e:
        block(
            f"Failed to parse hook input as JSON.\n"
            f"Parse error: {e}\n"
            f"This hook fails closed on malformed input."
        )

    if not isinstance(payload, dict):
        block("Hook input must be a JSON object.")

    # Infinite-loop guard: a previous turn set decision:block and Claude is
    # retrying. Do nothing this turn, regardless of config.
    if payload.get("stop_hook_active"):
        sys.exit(0)

    config = load_config()
    if not config.get("enabled", False):
        sys.exit(0)

    # Phase 1: observe-only. Log and exit.
    audit_log(config, payload)
    sys.exit(0)


def main() -> None:
    try:
        run()
    except SystemExit:
        raise
    except Exception:
        # Unhandled error → fail closed with a paper trail.
        tb = traceback.format_exc()
        block(f"Unhandled exception in hook:\n{tb}")


if __name__ == "__main__":
    main()
