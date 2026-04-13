---
name: secrets-scan
description: Scan the working tree or staged files for hardcoded secrets, API keys, tokens, and credentials using pattern matching. Reports findings with file and line references.
---

# secrets-scan

Scans source files for hardcoded secrets, API keys, tokens, and credentials using regex pattern matching and entropy analysis.

## How to invoke

```
/secrets-scan [options] [path...]
```

## Examples

```bash
# Scan staged files (default)
secrets-scan

# Scan the entire working tree
secrets-scan --all

# Scan a specific directory
secrets-scan src/

# Scan multiple paths
secrets-scan src/ config/
```

## What It Detects

- **AWS access keys**: `AKIA` prefix patterns with associated secrets
- **GitHub tokens**: `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_` prefixed strings
- **Slack tokens**: `xoxb-`, `xoxp-`, `xoxo-`, `xoxa-` prefixed strings
- **Stripe keys**: `sk_live_`, `rk_live_`, `pk_live_` prefixed strings
- **Private keys**: PEM-encoded private keys (`-----BEGIN ... PRIVATE KEY-----`)
- **JWT tokens**: Base64-encoded three-part tokens (`eyJ...`)
- **Connection strings**: URIs with embedded passwords (`postgres://user:pass@`, `mongodb://...`)
- **Generic API keys**: high-entropy strings assigned to variables named `key`, `secret`, `token`, `password`, `api_key`, etc.
- **`.env` files**: environment files that may contain secrets

## What It Skips

- Binary files
- Files matching `.gitignore` patterns
- Known test/placeholder values (`sk_test_`, `pk_test_`, `example`, `placeholder`, `changeme`, `xxx`)
- Lock files (`package-lock.json`, `yarn.lock`, `poetry.lock`, etc.)

## Output Format

```
src/config.py:12  [AWS_KEY]     AKIA...REDACTED
src/auth.ts:45    [PRIVATE_KEY] -----BEGIN RSA PR...
src/.env:3        [ENV_SECRET]  DATABASE_URL=post...
```

Exit code 0 if clean, 1 if secrets found.

## Architecture

- `SKILL.md` — This file
- `secrets-scan` — Executable Python script
