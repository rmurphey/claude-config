#!/usr/bin/env python3
"""Tests for secrets-scan executable.

Tests pattern detection, false positive filtering, entropy analysis,
and file handling. Each test creates temporary files to avoid depending
on external state.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent / "secrets-scan"


def run_scan(*args: str, files: dict[str, str] | None = None) -> tuple[int, str, str]:
    """Run secrets-scan with given args and optional temp files.

    Args:
        *args: CLI arguments to pass to the script.
        files: dict of {filename: content} to create in a temp dir.
               If provided, the temp dir path is appended to args.

    Returns:
        (exit_code, stdout, stderr)
    """
    cmd_args = [sys.executable, str(SCRIPT_PATH), *args]

    if files is not None:
        with tempfile.TemporaryDirectory() as tmpdir:
            for name, content in files.items():
                filepath = Path(tmpdir) / name
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)
            cmd_args.append(tmpdir)
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout, result.stderr


def scan_file(filename: str, content: str) -> tuple[int, str, str]:
    """Convenience: scan a single temp file."""
    return run_scan(files={filename: content})


# --- Pattern Detection Tests ---


class TestAWSKeyDetection:
    def test_detects_aws_access_key(self):
        rc, stdout, _ = scan_file("config.py", 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
        assert rc == 1
        assert "AWS_KEY" in stdout

    def test_detects_aws_key_in_yaml(self):
        rc, stdout, _ = scan_file("config.yaml", "aws_access_key_id: AKIAIOSFODNN7EXAMPLE\n")
        assert rc == 1
        assert "AWS_KEY" in stdout

    def test_detects_aws_secret_key(self):
        rc, stdout, _ = scan_file(
            "config.py",
            'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n',
        )
        assert rc == 1
        assert "AWS_SECRET" in stdout


class TestGitHubTokenDetection:
    def test_detects_classic_pat(self):
        token = "ghp_" + "A" * 36
        rc, stdout, _ = scan_file("env.sh", f'GITHUB_TOKEN="{token}"\n')
        assert rc == 1
        assert "GITHUB_TOKEN" in stdout

    def test_detects_fine_grained_pat(self):
        token = "ghp_" + "B" * 40
        rc, stdout, _ = scan_file("ci.yml", f"token: {token}\n")
        assert rc == 1
        assert "GITHUB_TOKEN" in stdout

    def test_detects_oauth_token(self):
        token = "gho_" + "C" * 36
        rc, stdout, _ = scan_file("auth.py", f'TOKEN = "{token}"\n')
        assert rc == 1
        assert "GITHUB_TOKEN" in stdout


class TestSlackTokenDetection:
    def test_detects_bot_token(self):
        rc, stdout, _ = scan_file("slack.py", 'TOKEN = "xoxb-1234567890-abcdefghij"\n')
        assert rc == 1
        assert "SLACK_TOKEN" in stdout


class TestStripeKeyDetection:
    def test_detects_live_secret_key(self):
        key = "sk_live_" + "a" * 24
        rc, stdout, _ = scan_file("billing.ts", f'const key = "{key}";\n')
        assert rc == 1
        assert "STRIPE_KEY" in stdout

    def test_skips_test_key(self):
        key = "sk_test_" + "a" * 24
        rc, stdout, _ = scan_file("billing.ts", f'const key = "{key}";\n')
        assert rc == 0
        assert "No secrets" in stdout


class TestPrivateKeyDetection:
    def test_detects_rsa_private_key(self):
        rc, stdout, _ = scan_file(
            "key.pem",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQ...\n",
        )
        assert rc == 1
        assert "PRIVATE_KEY" in stdout

    def test_detects_generic_private_key(self):
        rc, stdout, _ = scan_file(
            "key.pem",
            "-----BEGIN PRIVATE KEY-----\nMIIEpAIBAAKCAQ...\n",
        )
        assert rc == 1
        assert "PRIVATE_KEY" in stdout

    def test_detects_ec_private_key(self):
        rc, stdout, _ = scan_file(
            "ec.pem",
            "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEI...\n",
        )
        assert rc == 1
        assert "PRIVATE_KEY" in stdout


class TestConnectionStringDetection:
    def test_detects_postgres_connection(self):
        rc, stdout, _ = scan_file(
            "db.py",
            'DATABASE_URL = "postgres://admin:secretpass@db.internal:5432/mydb"\n',
        )
        assert rc == 1
        assert "CONNECTION_STRING" in stdout

    def test_detects_mongodb_connection(self):
        rc, stdout, _ = scan_file(
            "db.js",
            'const uri = "mongodb://root:p4ssw0rd@mongo.internal:27017/app";\n',
        )
        assert rc == 1
        assert "CONNECTION_STRING" in stdout

    def test_skips_connection_with_placeholder_password(self):
        rc, stdout, _ = scan_file(
            "db.py",
            'DATABASE_URL = "postgres://admin:changeme@localhost:5432/dev"\n',
        )
        assert rc == 0


class TestJWTDetection:
    def test_detects_jwt_token(self):
        # Minimal valid-looking JWT structure
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        rc, stdout, _ = scan_file("auth.ts", f'const token = "{jwt}";\n')
        assert rc == 1
        assert "JWT_TOKEN" in stdout


class TestGenericSecretDetection:
    def test_detects_password_assignment(self):
        rc, stdout, _ = scan_file(
            "config.py",
            'password = "hunter2isnotasecurepassword"\n',
        )
        assert rc == 1
        assert "GENERIC_SECRET" in stdout

    def test_detects_api_key_assignment(self):
        rc, stdout, _ = scan_file(
            "config.js",
            'const api_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3";\n',
        )
        assert rc == 1

    def test_skips_short_values(self):
        rc, _, _ = scan_file("config.py", 'password = "short"\n')
        assert rc == 0


class TestGoogleAPIKeyDetection:
    def test_detects_google_api_key(self):
        key = "AIza" + "A" * 35
        rc, stdout, _ = scan_file("maps.js", f'const key = "{key}";\n')
        assert rc == 1
        assert "GOOGLE_API_KEY" in stdout


class TestSendgridKeyDetection:
    def test_detects_sendgrid_key(self):
        key = "SG." + "A" * 22 + "." + "B" * 43
        rc, stdout, _ = scan_file("email.py", f'SENDGRID_KEY = "{key}"\n')
        assert rc == 1
        assert "SENDGRID_KEY" in stdout


# --- False Positive Filtering ---


class TestFalsePositiveFiltering:
    def test_skips_placeholder_values(self):
        rc, _, _ = scan_file(
            "config.py",
            'api_key = "your_api_key_here_placeholder"\n',
        )
        assert rc == 0

    def test_skips_example_values_in_generic_secrets(self):
        rc, _, _ = scan_file(
            "config.py",
            'token = "this-is-an-example-token-value"\n',
        )
        assert rc == 0

    def test_does_not_skip_aws_key_containing_example(self):
        """AWS key format is definitive — 'EXAMPLE' in the suffix is irrelevant."""
        rc, stdout, _ = scan_file(
            "config.py",
            'KEY = "AKIAIOSFODNN7EXAMPLE"\n',
        )
        assert rc == 1
        assert "AWS_KEY" in stdout

    def test_does_not_skip_github_token_with_test_in_value(self):
        """Token format is definitive — substrings don't make it a false positive."""
        token = "ghp_" + "testABCDEFGHIJKLMNOPtest12345678"
        rc, stdout, _ = scan_file("ci.yml", f"token: {token}\n")
        assert rc == 1
        assert "GITHUB_TOKEN" in stdout

    def test_skips_stripe_test_key(self):
        key = "sk_test_" + "a" * 24
        rc, _, _ = scan_file("billing.ts", f'const key = "{key}";\n')
        assert rc == 0

    def test_skips_connection_string_with_dummy_password(self):
        rc, _, _ = scan_file(
            "db.py",
            'DB_URL = "postgres://user:dummy_password@localhost:5432/dev"\n',
        )
        assert rc == 0

    def test_skips_commented_lines(self):
        rc, _, _ = scan_file(
            "config.py",
            '# password = "realsecretpasswordvalue"\n',
        )
        assert rc == 0

    def test_skips_js_commented_lines(self):
        rc, _, _ = scan_file(
            "config.js",
            '// const token = "ghp_' + "A" * 36 + '";\n',
        )
        assert rc == 0


# --- Entropy Detection ---


class TestEntropyDetection:
    def test_detects_high_entropy_secret(self):
        # High entropy string in a secret-named variable
        rc, stdout, _ = scan_file(
            "config.py",
            'signing_key = "k8s7j2m4p9q1x6v3w0z5n8b4f7h2t9r"\n',
        )
        assert rc == 1
        assert "HIGH_ENTROPY" in stdout

    def test_skips_low_entropy_value(self):
        # Low entropy (repeated chars) — not a secret
        rc, _, _ = scan_file(
            "config.py",
            'encryption_key = "aaaaaaaabbbbbbbbcccccccc"\n',
        )
        assert rc == 0


# --- .env File Handling ---


class TestEnvFileHandling:
    def test_detects_secrets_in_env_file(self):
        rc, stdout, _ = scan_file(
            ".env",
            "DATABASE_URL=postgres://user:realpassword@db:5432/prod\n"
            "SECRET_KEY=a8f3b2c1d0e9f8a7b6c5d4e3f2a1b0c9\n",
        )
        assert rc == 1
        assert "ENV_SECRET" in stdout

    def test_skips_env_comments(self):
        rc, _, _ = scan_file(
            ".env",
            "# SECRET_KEY=notrealvalue\n"
            "APP_NAME=myapp\n",
        )
        assert rc == 0

    def test_skips_env_placeholder_values(self):
        rc, _, _ = scan_file(
            ".env",
            "API_KEY=changeme\n"
            "SECRET=your_secret_here\n",
        )
        assert rc == 0


# --- File Handling ---


class TestFileHandling:
    def test_skips_lock_files(self):
        rc, _, _ = run_scan(files={
            "package-lock.json": '{"secret_key": "sk_live_' + "a" * 24 + '"}',
            "clean.py": "x = 1\n",
        })
        assert rc == 0

    def test_clean_file_exits_zero(self):
        rc, stdout, _ = scan_file(
            "app.py",
            "import os\n\nMAX_RETRIES = 3\nBASE_URL = 'https://api.example.com'\n",
        )
        assert rc == 0
        assert "No secrets" in stdout

    def test_multiple_secrets_in_one_file(self):
        content = (
            'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
            'STRIPE = "sk_live_' + "a" * 24 + '"\n'
            'TOKEN = "ghp_' + "B" * 36 + '"\n'
        )
        rc, stdout, _ = scan_file("config.py", content)
        assert rc == 1
        assert "AWS_KEY" in stdout
        assert "STRIPE_KEY" in stdout
        assert "GITHUB_TOKEN" in stdout

    def test_no_staged_files_message(self):
        """When run without args and no staged files, should print help message."""
        rc, stdout, _ = run_scan()
        assert rc == 0
        assert "staged" in stdout.lower() or "No secrets" in stdout


# --- Output Format ---


class TestOutputFormat:
    def test_output_includes_file_and_line(self):
        rc, stdout, _ = scan_file(
            "secret.py",
            'x = 1\nAPI_KEY = "AKIAIOSFODNN7EXAMPLE"\n',
        )
        assert rc == 1
        assert "secret.py:2" in stdout

    def test_output_redacts_values(self):
        key = "AKIAIOSFODNN7EXAMPLE"
        rc, stdout, _ = scan_file("config.py", f'KEY = "{key}"\n')
        assert rc == 1
        # Full key should NOT appear in output
        assert key not in stdout
        assert "REDACTED" in stdout

    def test_output_includes_count(self):
        content = (
            'KEY1 = "AKIAIOSFODNN7EXAMPLE"\n'
            'KEY2 = "sk_live_' + "a" * 24 + '"\n'
        )
        rc, stdout, _ = scan_file("config.py", content)
        assert rc == 1
        assert "2 potential secret(s)" in stdout
