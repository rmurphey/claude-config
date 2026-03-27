# check-prose

Checks markdown files for banned phrases defined in CLAUDE.md files and unfilled placeholders.

## Usage

```bash
check-prose [directory...]
```

If no directories are given, checks all `.md` files in the current directory (recursive).

## Examples

```bash
# Check all markdown files in the project
check-prose

# Check only application-facing files
check-prose application/

# Check specific directories
check-prose application/ prep/
```

## What It Does

1. Reads `~/.claude/CLAUDE.md` (global) and `./CLAUDE.md` (project) for banned phrase lists
2. Extracts individual phrases from "Writing standards", "Banned", and "Never use" sections
3. Greps all `.md` files for matches (case-insensitive)
4. Checks for unfilled placeholders (`[PLACEHOLDER]` patterns that aren't markdown links)
5. Reports violations with file:line references
6. Exits 0 if clean, 1 if violations found

## How Banned Phrases Are Discovered

The skill dynamically reads CLAUDE.md files at runtime. It extracts phrases from:
- Lines with quoted phrases: `"phrase here"`
- Lines with bold-quoted phrases: `**"phrase here"**`
- Slash-separated alternatives: `"phrase A" / "phrase B"`

This means adding a new banned phrase to any CLAUDE.md automatically includes it in future checks.

## Architecture

- `SKILL.md` -- This file
- `check-prose` -- Executable Python script
