#!/usr/bin/env python3
"""Tests for output-to-file-detect.py Stop hook.

Phase 1 scope: skeleton hook.
  - Config loading (missing / malformed / valid) with fail-closed semantics
  - `enabled: false` short-circuits to exit 0
  - `stop_hook_active: true` short-circuits to exit 0 (infinite-loop guard)
  - Fail-closed on unparseable stdin
  - Audit log appends a payload entry per invocation when enabled
  - Audit log creates its parent directory on first write
  - Audit log write failure is fail-open (exit 0, warning on stderr)
  - Unexpected exceptions exit 2 (fail closed)

Phase 2 (detection / threshold / escalation) is deliberately NOT covered here.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent / "output-to-file-detect.py"


def run_hook(
    payload: dict | str,
    config: dict | None = None,
    tmp_dir: Path | None = None,
    env_override: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Invoke the hook and return (exit_code, stdout, stderr).

    `payload` may be a dict (serialized to JSON) or a raw string (for malformed
    stdin tests). `config`, if provided, is written to a temp file and exposed
    via OUTPUT_TO_FILE_CONFIG. `env_override` merges into the subprocess env.
    """
    env = os.environ.copy()
    env.pop("OUTPUT_TO_FILE_CONFIG", None)

    if config is not None:
        assert tmp_dir is not None, "pass tmp_path when providing config"
        config_path = tmp_dir / "config.json"
        config_path.write_text(json.dumps(config))
        env["OUTPUT_TO_FILE_CONFIG"] = str(config_path)

    if env_override:
        env.update(env_override)

    stdin_text = payload if isinstance(payload, str) else json.dumps(payload)

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError("Hook timed out after 10s") from None

    return result.returncode, result.stdout, result.stderr


def make_payload(
    session_id: str = "sess-test",
    transcript_path: str | None = None,
    stop_hook_active: bool = False,
) -> dict:
    return {
        "session_id": session_id,
        "transcript_path": transcript_path or "/nonexistent/transcript.jsonl",
        "stop_hook_active": stop_hook_active,
    }


# --- Short-circuit paths ---


class TestShortCircuits:
    """Paths that must exit 0 immediately without touching anything else."""

    def test_stop_hook_active_exits_zero(self, tmp_path):
        """stop_hook_active=true MUST exit 0 immediately — infinite-loop guard.

        The short-circuit is absolute: it runs before load_config() and
        before audit_log(), so no audit entry should ever be produced.
        """
        log_path = tmp_path / "audit.log"
        config = {"enabled": True, "audit_log": str(log_path)}
        rc, stdout, stderr = run_hook(
            make_payload(stop_hook_active=True), config=config, tmp_dir=tmp_path
        )
        assert rc == 0, stderr
        assert not log_path.exists(), \
            "stop_hook_active must short-circuit before audit_log() is called"

    def test_enabled_false_exits_zero(self, tmp_path):
        config = {"enabled": False, "audit_log": str(tmp_path / "audit.log")}
        rc, _, stderr = run_hook(make_payload(), config=config, tmp_dir=tmp_path)
        assert rc == 0, stderr


# --- Fail-closed on bad stdin / bad config ---


class TestFailClosed:
    """The hook must NEVER silently pass when it cannot do its job."""

    def test_invalid_json_stdin_blocks(self, tmp_path):
        rc, _, stderr = run_hook("not json", config={"enabled": True}, tmp_dir=tmp_path)
        assert rc == 2
        assert "parse" in stderr.lower() or "json" in stderr.lower()

    def test_explicit_missing_config_blocks(self):
        """OUTPUT_TO_FILE_CONFIG points at nonexistent file → fail closed."""
        rc, _, stderr = run_hook(
            make_payload(),
            env_override={"OUTPUT_TO_FILE_CONFIG": "/nonexistent/config.json"},
        )
        assert rc == 2
        assert "config" in stderr.lower()

    def test_malformed_config_blocks(self, tmp_path):
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{not valid json")
        rc, _, stderr = run_hook(
            make_payload(),
            env_override={"OUTPUT_TO_FILE_CONFIG": str(bad_path)},
        )
        assert rc == 2
        assert "config" in stderr.lower()

    def test_missing_default_config_does_not_crash(self):
        """Unset env var → use default path. Must not crash (exit 1) even
        when the default config file doesn't exist at test time."""
        env_override = {"HOME": "/tmp/definitely-no-claude-dir-here"}
        rc, _, stderr = run_hook(make_payload(), env_override=env_override)
        # Acceptable: 0 (no default config, treat as disabled) or 2 (fail closed
        # with clear message). NOT 1 (unhandled crash).
        assert rc in (0, 2), f"Hook crashed unexpectedly: rc={rc} stderr={stderr}"


# --- Audit logging ---


class TestAuditLogging:
    def test_logs_payload_when_enabled(self, tmp_path):
        log_path = tmp_path / "audit.log"
        config = {"enabled": True, "audit_log": str(log_path)}
        rc, _, stderr = run_hook(
            make_payload(session_id="sess-abc"), config=config, tmp_dir=tmp_path
        )
        assert rc == 0, stderr
        assert log_path.exists()
        content = log_path.read_text()
        assert content, "audit log should have at least one entry"
        entries = [json.loads(line) for line in content.strip().splitlines()]
        assert len(entries) == 1
        assert entries[0].get("session_id") == "sess-abc"
        assert entries[0].get("phase") == 1, \
            "Phase 1 invariant: log entries must be marked phase=1"
        assert entries[0].get("timestamp"), "log entries must include a timestamp"

    def test_creates_log_directory_on_first_write(self, tmp_path):
        log_path = tmp_path / "newdir" / "nested" / "audit.log"
        assert not log_path.parent.exists()
        config = {"enabled": True, "audit_log": str(log_path)}
        rc, _, stderr = run_hook(make_payload(), config=config, tmp_dir=tmp_path)
        assert rc == 0, stderr
        assert log_path.exists()

    def test_audit_log_write_failure_fails_open(self, tmp_path):
        """If the log cannot be written (unwritable path), the hook must
        still exit 0 and not wedge the session. Logging is best-effort,
        but the failure must surface as a stderr warning."""
        # Parent is a regular file, so mkdir fails with ENOTDIR. Reliable
        # across Unix targets regardless of uid (root included).
        blocker = tmp_path / "blocker"
        blocker.write_text("i am a file, not a directory")
        log_path = blocker / "audit.log"
        config = {"enabled": True, "audit_log": str(log_path)}
        rc, _, stderr = run_hook(make_payload(), config=config, tmp_dir=tmp_path)
        assert rc == 0, f"audit log failure should be fail-open; got rc={rc} stderr={stderr}"
        assert "audit log" in stderr.lower(), \
            "fail-open path must emit a visible stderr warning"

    def test_enabled_false_does_not_log(self, tmp_path):
        log_path = tmp_path / "audit.log"
        config = {"enabled": False, "audit_log": str(log_path)}
        rc, _, _ = run_hook(make_payload(), config=config, tmp_dir=tmp_path)
        assert rc == 0
        assert not log_path.exists() or log_path.read_text() == ""


# --- Phase 1 no-op behavior ---


class TestPhase1NoOp:
    """Phase 1 hook must NOT block or emit decisions — only log and exit 0.

    Detection / threshold / escalation logic belongs to Phase 2. Until then,
    enabled=true means 'observe and log' — never 'block'.
    """

    def test_enabled_true_never_blocks_phase1(self, tmp_path):
        log_path = tmp_path / "audit.log"
        config = {"enabled": True, "audit_log": str(log_path)}
        rc, stdout, _ = run_hook(make_payload(), config=config, tmp_dir=tmp_path)
        assert rc == 0
        # No Stop-hook block decision emitted
        if stdout.strip():
            parsed = json.loads(stdout)
            assert parsed.get("decision") != "block", \
                "Phase 1 skeleton must not emit block decisions"
