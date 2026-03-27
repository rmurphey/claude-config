---
name: validate-config
description: Validate the Claude Code configuration directory for consistency, completeness, and correctness. Checks hook scripts, skill structure, agent frontmatter, and permission patterns.
---

# validate-config

Validates the Claude Code config directory (`~/.claude/`) for structural integrity.

## How to invoke

```
/validate-config
```

## What It Checks

1. **Hook script references** — Every script path in `settings.json` hooks exists and is executable
2. **Skill structure** — Every directory in `skills/` has a `SKILL.md`; executable scripts are actually executable
3. **Agent frontmatter** — Every `.md` file in `agents/` has required YAML frontmatter fields (`name`, `description`, `tools`)
4. **Permission syntax** — Patterns in `settings.json` `permissions.allow` follow `Tool` or `Tool(pattern)` format
5. **Duplicate permissions** — No duplicate entries in the `permissions.allow` array
6. **Hook structure** — Hook entries have required fields (`type`, `command`)

## Output

Reports all issues found, grouped by category. Exit code 0 if clean, 1 if any issues found.

## Limitations

- Permission pattern validation is syntactic only — it does not verify that referenced paths exist
- Agent frontmatter parsing uses simple text matching, not a full YAML parser (avoids external dependencies)
- Does not validate hook command logic, only that referenced script files exist

## Architecture

- `SKILL.md` — This file
- `validate-config` — Executable Python script
