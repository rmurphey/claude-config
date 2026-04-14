---
name: changelog
description: Generate a changelog from git commits between two refs (tags, branches, or SHAs). Groups entries by conventional commit prefix and formats as Markdown.
---

# changelog

Generate a changelog from git history.

## How to invoke

```
/changelog [from] [to]
```

## Examples

```bash
# Changelog since last tag to HEAD
/changelog

# Changelog between two tags
/changelog v1.2.0 v1.3.0

# Changelog from a specific commit to HEAD
/changelog abc1234

# Changelog between two branches
/changelog main release/2.0
```

## What You Must Do

### Step 1: Determine the range

- If no arguments: find the most recent tag with `git describe --tags --abbrev=0` and use `<tag>..HEAD`
- If one argument: use `<arg>..HEAD`
- If two arguments: use `<from>..<to>`
- If no tags exist and no arguments: use the last 20 commits

### Step 2: Collect commits

Run:
```
git log --pretty=format:"%H|%s|%an|%ad" --date=short <range>
```

### Step 3: Parse and group

Group commits by conventional commit prefix:

- **Features** (`feat:`) — new functionality
- **Bug Fixes** (`fix:`) — corrections
- **Performance** (`perf:`) — performance improvements
- **Refactoring** (`refactor:`) — code restructuring without behavior change
- **Documentation** (`docs:`) — documentation changes
- **Tests** (`test:`) — test additions or modifications
- **Chores** (`chore:`, `ci:`, `build:`, `style:`) — maintenance

Strip the prefix from each message for cleaner display. Drop the `Co-Authored-By` trailer.

### Step 4: Format output

```markdown
# Changelog

## [Unreleased] — YYYY-MM-DD

### Features
- Short description of feature (abc1234)
- Another feature (def5678)

### Bug Fixes
- Description of fix (ghi9012)

### Refactoring
- Description (jkl3456)

### Documentation
- Description (mno7890)

### Tests
- Description (pqr1234)

### Chores
- Description (stu5678)
```

Omit empty sections. Include the short SHA for each entry.

### Step 5: Present to user

Display the formatted changelog. Ask if they want to:
- Save it to a CHANGELOG.md file
- Copy it for a GitHub release
- Adjust the format

## Rules

- **Respect conventional commit structure** — if commits don't use conventional prefixes, group as "Changes" with the full message
- **Drop bot trailers** — strip `Co-Authored-By`, `Signed-off-by`, etc.
- **Keep entries concise** — one line per commit, no body text
- **Include date range** — show the date span in the header

## Architecture

- `SKILL.md` — This file (instruction-based skill, no executable)
