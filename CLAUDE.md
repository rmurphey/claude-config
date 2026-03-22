# Global Claude Code Guidelines

These are default development principles that apply across all projects unless overridden by project-specific CLAUDE.md files.

## Core Principles

1. **Do what has been asked; nothing more, nothing less**
2. **TDD for all non-documentation changes** - write failing test first, then implement. If a file is difficult to test, that is evidence of an antipattern — stop and ask the user whether to refactor for testability or skip TDD for this change. Never silently decide to skip.
3. **Read before editing** - always read a file before attempting to modify it
4. **No magic numbers** - use named constants
5. **Search before struggling** - if an approach fails twice or a problem feels intractable, stop and search online (WebSearch/WebFetch) for documentation, examples, or known issues. Do not keep retrying the same failing approach. Searching is always cheaper than spinning.

## Language Defaults

- **JS/TS**: `camelCase` for variables/functions, `PascalCase` for classes/components, `UPPER_SNAKE_CASE` for constants
- **Python**: `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants

## Git Discipline

- **NEVER bypass pre-commit hooks** - `git commit --no-verify` is forbidden
- **NEVER bypass pre-push hooks** - `git push --no-verify` is forbidden
- Fix the issues instead of skipping safety checks
- Make atomic commits with descriptive messages
- **Conventional Commits** — use `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:` prefixes
- **Branch naming** — `{your-prefix}/{feature-name}` (e.g. `rm/add-auth`)

## Test Integrity Policy

Claude must NEVER auto-fix tests solely to make them pass.

When tests fail after code changes:
1. STOP and report the failure
2. Explain what tests are failing and why
3. Ask the operator to decide:
   - Are the code changes correct? (tests need legitimate update)
   - Did the code changes introduce a bug? (code should be fixed)

**Allowed test changes:**
- Adding new tests for new functionality
- Refactoring tests (renaming, reorganizing)
- Updating tests when operator explicitly approves

**Blocked test changes:**
- Changing assertion expected values without approval
- Removing failing tests
- Weakening test assertions to make them pass

## Communication Style

- Answer directly without preambles
- Never say "You're right" or agreement variations
- Never include implementation timelines
- Present brief tradeoffs, then give a clear recommendation

## Pull Requests

- Detailed PR descriptions: context/motivation, approach taken, alternatives considered, testing performed
- Always include a test plan section

## Error Prevention

Before ANY code change:
- Check existing imports for type patterns
- Verify field names in actual data structures
- Look for constants files before using literals

## Code Review Checklist

After completing any code change, review it against all of the following before presenting it:

1. **Tests** — Are there tests for the change? Do existing tests still pass? Flag any untested paths.
2. **Architecture** — Does the change fit the existing patterns and boundaries? Flag any new coupling, layering violations, or responsibility shifts.
3. **Maintainability** — Is the code easy to modify later? Flag duplication, unclear naming, or implicit contracts.
4. **Readability** — Can someone unfamiliar with the change understand it on first read? Flag clever tricks, deep nesting, or missing context.
5. **Documentation** — Are public APIs, non-obvious behavior, and configuration changes documented where they'll be found?
6. **Blast radius** — What else could this break? Flag shared utilities, database migrations, API contracts, or config changes that affect other consumers.
7. **Functionality** — Does the change actually do what was requested, completely and correctly?

If any item surfaces a concern, raise it before marking the work done.

## Writing standards — zero tolerance

Never use these phrases:
- "the real question is"
- "let's dive in" / "let's dive deeper" / "deep dive"
- "it's worth noting" / "it's worth mentioning"
- "here's the thing"
- "at the end of the day"
- "game-changer"
- "navigate" / "unlock" / "leverage" / "landscape" / "embrace" (non-literal)
- "we'd be better off"
- "in today's [anything]"
- "move the needle" / "level up" / "lean into" / "double down"
- "unpack" / "take a step back"

Never use these structural patterns:
- "It's not about X, it's about Y" reframes
- Rhetorical questions that restate what was just said
- Tidy thesis-restating closings that repackage the argument
- Opening with "Imagine..." or "Picture this..."
- Any sentence generic enough to appear in any LinkedIn post on any topic

When a piece has made its point, stop. Do not add a closing that restates the argument. If in doubt about whether a sentence is filler, delete it.
