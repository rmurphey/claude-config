# claude-config

Personal [Claude Code](https://docs.claude.com/en/docs/claude-code) configuration.

## Layout

```
agents/      — specialized reviewer subagents (Python, TypeScript, React, CSS, shell, tests, security, privacy, defensive design, AI security, dependencies, observability, writing)
skills/      — user-invocable slash commands (/commit, /push, /review-pr, /changelog, /secrets-scan, /pr-description, /validate-config, /check-prose, /dead-files, /md2latex, /sync-pdfs)
hooks/       — PreToolUse and PostToolUse enforcement hooks (TDD, atomic commits, skill governance, pre-push review, pre-execution Python review)
plans/       — scratch space for planning documents (gitignored)
settings.json — Claude Code settings: permissions, hook registrations, plugins
CLAUDE.md    — global development principles that apply across all projects
.gitignore   — excludes session transcripts, caches, and runtime state
```

## Notes

- Paths in `settings.json` are hardcoded to the author's home directory (`~/.claude/...`). Reusing this config on another machine requires rewriting those paths.
- Some hooks depend on Python 3 and `pytest` (`pip3 install pytest`).
- Skills under `skills/*/` may have executable scripts that must remain executable (`chmod +x`).
- Test suites for hooks and skills live alongside them (`test_*.py` files) and use `pytest`.

## Running the test suites

```bash
python3 -m pytest hooks/test_*.py skills/secrets-scan/test_*.py -v
```

## Validating the config

```bash
./skills/validate-config/validate-config
```

Checks hook script references, skill structure, agent frontmatter, and permission syntax.
