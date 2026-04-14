#!/usr/bin/env python3
"""Tests for pre-exec-python.py PreToolUse hook.

Tests command detection, dangerous pattern scanning, advisory output,
and edge cases. Uses subprocess to invoke the hook with controlled stdin.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent / "pre-exec-python.py"


def run_hook(
    tool_input: dict,
    tool_name: str = "Bash",
) -> tuple[int, str, str]:
    """Run the hook with given input. Returns (exit_code, stdout, stderr)."""
    payload = {
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    env = os.environ.copy()
    env.pop("SKILL_GOVERNANCE_CONFIG", None)

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


def run_with_script(command_template: str, script_content: str) -> tuple[int, str, str]:
    """Create a temp script file, run the hook against it."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(script_content)
        f.flush()
        script_path = f.name

    try:
        cmd = command_template.replace("{SCRIPT}", script_path)
        return run_hook({"command": cmd})
    finally:
        os.unlink(script_path)


# --- Passthrough ---


class TestPassthrough:
    """Non-Python commands should exit 0 with no output."""

    def test_non_python_command_passes(self):
        rc, stdout, _ = run_hook({"command": "git status"})
        assert rc == 0
        assert stdout.strip() == ""

    def test_non_bash_tool_passes(self):
        rc, stdout, _ = run_hook({"command": "anything"}, tool_name="Edit")
        assert rc == 0
        assert stdout.strip() == ""

    def test_python_m_module_passes(self):
        """python -m should not trigger script scanning."""
        rc, stdout, _ = run_hook({"command": "python3 -m pytest tests/"})
        assert rc == 0
        assert stdout.strip() == ""

    def test_python_c_command_passes(self):
        """python -c should not trigger script scanning."""
        rc, stdout, _ = run_hook({"command": 'python3 -c "print(1)"'})
        assert rc == 0
        assert stdout.strip() == ""

    def test_nonexistent_script_passes(self):
        rc, stdout, _ = run_hook({"command": "python3 /nonexistent/script.py"})
        assert rc == 0
        assert stdout.strip() == ""

    def test_invalid_json_passes(self):
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="not json",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0


# --- Never blocks ---


class TestNeverBlocks:
    """The hook must ALWAYS exit 0 — it advises, never blocks."""

    def test_dangerous_script_still_exits_zero(self):
        rc, _, _ = run_with_script(
            "python3 {SCRIPT}",
            'import os\nos.system("rm -rf /")\n',
        )
        assert rc == 0

    def test_clean_script_exits_zero(self):
        rc, _, _ = run_with_script(
            "python3 {SCRIPT}",
            "print('hello world')\n",
        )
        assert rc == 0


# --- Pattern Detection ---


class TestEvalExec:
    def test_detects_eval(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'result = eval(user_input)\n',
        )
        assert "EVAL/EXEC" in stdout

    def test_detects_exec(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'exec(code_string)\n',
        )
        assert "EVAL/EXEC" in stdout


class TestPickle:
    def test_detects_pickle_load(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import pickle\ndata = pickle.load(f)\n',
        )
        assert "PICKLE_LOAD" in stdout

    def test_detects_pickle_loads(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import pickle\ndata = pickle.loads(payload)\n',
        )
        assert "PICKLE_LOAD" in stdout


class TestShellInjection:
    def test_detects_shell_true(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import subprocess\nsubprocess.run(cmd, shell=True)\n',
        )
        assert "SHELL_INJECTION" in stdout

    def test_detects_os_system(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import os\nos.system("ls -la")\n',
        )
        assert "OS_SYSTEM" in stdout


class TestTempfileRace:
    def test_detects_mktemp(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import tempfile\npath = tempfile.mktemp()\n',
        )
        assert "TEMP_MKTEMP" in stdout


class TestTLSVerification:
    def test_detects_verify_false(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import requests\nrequests.get(url, verify=False)\n',
        )
        assert "REQUESTS_NO_VERIFY" in stdout


class TestHardcodedSecrets:
    def test_detects_hardcoded_password(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'password = "supersecretpassword123"\n',
        )
        assert "HARDCODED_SECRET" in stdout

    def test_detects_hardcoded_api_key(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'api_key = "abcdef1234567890abcdef"\n',
        )
        assert "HARDCODED_SECRET" in stdout


class TestFilePermissions:
    def test_detects_chmod_777(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import os\nos.chmod("/tmp/file", 0o777)\n',
        )
        assert "CHMOD_777" in stdout


class TestRecursiveDelete:
    def test_detects_rmtree(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import shutil\nshutil.rmtree(path)\n',
        )
        assert "RM_RF" in stdout


# --- Clean scripts ---


class TestCleanScripts:
    def test_clean_script_no_output(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'import json\ndata = json.loads(\'{"key": "value"}\')\nprint(data)\n',
        )
        assert rc == 0
        assert stdout.strip() == ""

    def test_comments_are_skipped(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            '# eval(dangerous_code)\n# os.system("rm -rf /")\nprint("safe")\n',
        )
        assert rc == 0
        assert stdout.strip() == ""


# --- Command parsing ---


class TestCommandParsing:
    def test_detects_python3_command(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'eval(x)\n',
        )
        assert "EVAL/EXEC" in stdout

    def test_detects_python_command(self):
        rc, stdout, _ = run_with_script(
            "python {SCRIPT}",
            'eval(x)\n',
        )
        assert "EVAL/EXEC" in stdout


# --- Output format ---


class TestOutputFormat:
    def test_advisory_output_is_valid_json(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'eval(user_input)\n',
        )
        assert rc == 0
        data = json.loads(stdout)
        assert "hookSpecificOutput" in data
        assert "additionalContext" in data["hookSpecificOutput"]

    def test_output_includes_script_path(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'eval(x)\n',
        )
        data = json.loads(stdout)
        context = data["hookSpecificOutput"]["additionalContext"]
        assert ".py" in context

    def test_output_includes_line_number(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'x = 1\neval(user_input)\n',
        )
        data = json.loads(stdout)
        context = data["hookSpecificOutput"]["additionalContext"]
        assert "Line 2" in context

    def test_output_includes_finding_count(self):
        rc, stdout, _ = run_with_script(
            "python3 {SCRIPT}",
            'eval(x)\nos.system("cmd")\n',
        )
        data = json.loads(stdout)
        context = data["hookSpecificOutput"]["additionalContext"]
        assert "2 potential issue" in context
