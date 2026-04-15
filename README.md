# claude-config

A personal [Claude Code](https://docs.claude.com/en/docs/claude-code) configuration — agents, skills, and hooks you can clone and use directly, or copy individual pieces from.

## Installation

Clone into your home directory:

```bash
git clone https://github.com/rmurphey/claude-config.git ~/.claude
```

Paths in `settings.json` use `~/.claude/...`, so they resolve correctly for any user. No rewriting required.

## Layout

```
agents/      — specialized reviewer subagents (Python, TypeScript, React, CSS, shell, tests, security, privacy, defensive design, AI security, dependencies, observability, writing)
skills/      — user-invocable slash commands (/commit, /push, /review-pr, /changelog, /secrets-scan, /pr-description, /validate-config, /check-prose, /dead-files, /md2latex, /sync-pdfs)
hooks/       — PreToolUse and PostToolUse enforcement hooks (TDD, atomic commits, skill governance, pre-push review, pre-execution Python review)
settings.json — Claude Code settings: permissions, hook registrations, plugins
CLAUDE.md    — global development principles that apply across all projects
.gitignore   — excludes session transcripts, caches, and runtime state
```

## Requirements

- Python 3.9+ and `pytest` (`pip3 install pytest`) — for hook and skill tests
- `jq` — used by several hooks to parse JSON input
- Skills under `skills/*/` may include executable scripts; preserve the executable bit (`chmod +x`)

## Running the test suites

```bash
python3 -m pytest hooks/test_*.py skills/secrets-scan/test_*.py -v
```

## Validating the config

```bash
./skills/validate-config/validate-config
```

Checks hook script references, skill structure, agent frontmatter, and permission syntax.

## Using individual pieces

Each agent, skill, and hook is self-contained. Copy any `.md` file from `agents/` or any directory from `skills/` into your own `~/.claude/` to use it. Hooks require a corresponding registration in `settings.json`.
