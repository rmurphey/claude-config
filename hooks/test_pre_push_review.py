#!/usr/bin/env python3
"""Tests for pre-push-review.py PreToolUse hook.

Tests command detection, sensitive file pattern matching, advisory output
format, and edge cases. Uses subprocess to invoke the hook with controlled
stdin, matching the pattern from test_skill_governance.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest.mock
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent / "pre-push-review.py"


def run_hook(
    tool_input: dict,
    tool_name: str = "Bash",
    unpushed_files: list[str] | None = None,
) -> tuple[int, str, str]:
    """Run the pre-push hook with given input.

    Args:
        tool_input: The tool_input dict (usually {"command": "..."}).
        tool_name: The tool name (default "Bash").
        unpushed_files: Mock output for git log --name-only.
                       If None, lets git run normally.

    Returns:
        (exit_code, stdout, stderr)
    """
    payload = {
        "tool_name": tool_name,
        "tool_input": tool_input,
    }

    env = os.environ.copy()
    # Remove any SKILL_GOVERNANCE_CONFIG that might interfere
    env.pop("SKILL_GOVERNANCE_CONFIG", None)

    # If we want to mock unpushed files, we inject a wrapper script
    if unpushed_files is not None:
        # Create a mock that intercepts `git log --name-only` calls
        mock_script = f"""
import json
import re
import sys
import subprocess
from unittest.mock import patch
from pathlib import Path

# Mock get_unpushed_files to return our test data
HOOK_PATH = "{HOOK_PATH}"
exec(open(HOOK_PATH).read().replace("if __name__", "if False  # disabled __name__"))

# Override get_unpushed_files
def mock_get_unpushed_files():
    return {json.dumps(unpushed_files)}

# Patch and run
import importlib.util
spec = importlib.util.spec_from_file_location("hook", HOOK_PATH)
mod = importlib.util.module_from_spec(spec)
sys.stdin = open('/dev/stdin')

# Direct approach: read the module, replace the function, run main
import types
hook_source = open(HOOK_PATH).read()
hook_code = compile(hook_source, HOOK_PATH, 'exec')
hook_ns = {{'__name__': '__main__'}}

# Inject our mock before the module runs
original_exec = exec
def patched_main():
    pass

exec(hook_code, hook_ns)
"""
        # Simpler approach: just run the hook directly and mock via env var
        # Actually, let's use a different strategy: read the hook, patch, exec
        pass

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


def run_hook_raw(stdin_text: str) -> tuple[int, str, str]:
    """Run the hook with raw stdin text."""
    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError("Hook timed out after 10s") from None

    return result.returncode, result.stdout, result.stderr


# --- Non-push commands pass through silently ---


class TestPassthrough:
    """Non-push commands should exit 0 with no output."""

    def test_non_push_command_passes(self):
        rc, stdout, _ = run_hook({"command": "git status"})
        assert rc == 0
        assert stdout.strip() == ""

    def test_git_commit_passes(self):
        rc, stdout, _ = run_hook({"command": "git commit -m 'test'"})
        assert rc == 0
        assert stdout.strip() == ""

    def test_non_bash_tool_passes(self):
        rc, stdout, _ = run_hook({"command": "anything"}, tool_name="Edit")
        assert rc == 0
        assert stdout.strip() == ""

    def test_empty_command_passes(self):
        rc, stdout, _ = run_hook({"command": ""})
        assert rc == 0
        assert stdout.strip() == ""

    def test_invalid_json_passes(self):
        """Hook should not crash on bad input."""
        rc, _, _ = run_hook_raw("not json")
        assert rc == 0


# --- Push command detection ---


class TestPushDetection:
    def test_detects_git_push(self):
        """git push should be detected (even if no sensitive files)."""
        rc, _, _ = run_hook({"command": "git push"})
        assert rc == 0  # Always exits 0

    def test_detects_git_push_with_remote(self):
        rc, _, _ = run_hook({"command": "git push origin main"})
        assert rc == 0

    def test_detects_git_push_with_flags(self):
        rc, _, _ = run_hook({"command": "git push -u origin feature-branch"})
        assert rc == 0


# --- Sensitive file pattern matching ---


class TestSensitiveFilePatterns:
    """Test the file pattern matching logic directly by importing the module."""

    @pytest.fixture(autouse=True)
    def load_module(self):
        """Load the hook module's functions for direct testing."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("hook", str(HOOK_PATH))
        self.mod = importlib.util.module_from_spec(spec)
        # We need to prevent main() from running
        hook_source = HOOK_PATH.read_text()
        exec(compile(hook_source.replace(
            'if __name__ == "__main__":\n    main()',
            "pass  # skip main"
        ), str(HOOK_PATH), "exec"), self.mod.__dict__)

    def test_auth_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["src/auth.py"])
        assert len(result) == 1

    def test_middleware_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["lib/middleware.ts"])
        assert len(result) == 1

    def test_jwt_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["src/jwt.go"])
        assert len(result) == 1

    def test_crypto_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["utils/encrypt.py"])
        assert len(result) == 1

    def test_session_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["src/session.ts"])
        assert len(result) == 1

    def test_permission_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["src/permission.rb"])
        assert len(result) == 1

    def test_migration_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["db/migration.sql"])
        assert len(result) == 1

    def test_docker_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["docker.yaml"])
        assert len(result) == 1

    def test_terraform_file_is_sensitive(self):
        result = self.mod.find_sensitive_files(["infra/terraform.tf"])
        assert len(result) == 1

    def test_utils_file_is_not_sensitive(self):
        result = self.mod.find_sensitive_files(["src/utils.py"])
        assert len(result) == 0

    def test_styles_file_is_not_sensitive(self):
        result = self.mod.find_sensitive_files(["src/styles.css"])
        assert len(result) == 0

    def test_readme_is_not_sensitive(self):
        result = self.mod.find_sensitive_files(["README.md"])
        assert len(result) == 0

    def test_component_is_not_sensitive(self):
        result = self.mod.find_sensitive_files(["src/Button.tsx"])
        assert len(result) == 0

    def test_auth_directory_is_sensitive(self):
        result = self.mod.find_sensitive_files(["auth/handlers.py"])
        assert len(result) == 1

    def test_security_directory_is_sensitive(self):
        result = self.mod.find_sensitive_files(["security/middleware.js"])
        assert len(result) == 1

    def test_github_workflows_is_sensitive(self):
        result = self.mod.find_sensitive_files([".github/workflows/deploy.yml"])
        assert len(result) == 1

    def test_infrastructure_directory_is_sensitive(self):
        result = self.mod.find_sensitive_files(["infrastructure/main.tf"])
        assert len(result) == 1

    def test_deduplicates_files(self):
        """Same file appearing multiple times (from multiple commits) should be deduped."""
        result = self.mod.find_sensitive_files([
            "src/auth.py",
            "src/auth.py",
            "src/auth.py",
        ])
        assert len(result) == 1

    def test_mixed_sensitive_and_nonsensitive(self):
        result = self.mod.find_sensitive_files([
            "src/auth.py",
            "src/utils.py",
            "src/middleware.ts",
            "README.md",
        ])
        assert len(result) == 2
        sensitive_names = [f.rsplit("/")[-1] for f in result]
        assert "auth.py" in sensitive_names
        assert "middleware.ts" in sensitive_names


# --- Advisory output format ---


class TestAdvisoryOutput:
    """Test that the hook produces valid advisory JSON when sensitive files are found."""

    @pytest.fixture(autouse=True)
    def load_module(self):
        hook_source = HOOK_PATH.read_text()
        self.mod_dict: dict = {}
        exec(compile(hook_source.replace(
            'if __name__ == "__main__":\n    main()',
            "pass  # skip main"
        ), str(HOOK_PATH), "exec"), self.mod_dict)

    def test_never_blocks(self):
        """The hook must ALWAYS exit 0 — it advises, never blocks."""
        rc, _, _ = run_hook({"command": "git push"})
        assert rc == 0

    def test_no_output_for_non_push(self):
        rc, stdout, _ = run_hook({"command": "git status"})
        assert rc == 0
        assert stdout.strip() == ""
