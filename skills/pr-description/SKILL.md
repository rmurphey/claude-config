---
name: pr-description
description: Generate a PR description from the current branch's commits and diff against a base branch. Collects git context and outputs structured data for Claude to synthesize into a PR description following CLAUDE.md standards.
---

# pr-description

Collects git context for the current branch and outputs structured data for PR description authoring.

## How to invoke

```
/pr-description [base-branch]
```

If no base branch is given, defaults to `main`. Falls back to `master` if `main` does not exist.

## What It Does

1. Determines the base branch (argument, or `main`, or `master`)
2. Finds the merge base between the current branch and the base
3. Collects the commit log and full commit messages from merge base to HEAD
4. Collects diff stats and full diff (truncated at 8000 lines for large PRs)
5. Outputs all data in labeled sections

## How Claude Uses the Output

After running the script, synthesize a PR description with these sections from CLAUDE.md:

- **Context/Motivation** — Why this change exists, what problem it solves
- **Approach** — What was done, key design decisions
- **Alternatives considered** — What was rejected and why (or "None — straightforward change")
- **Testing** — What was tested, how to verify

Infer motivation from commit messages and the diff. For alternatives, look for reverted commits, fixup commits, or mention in commit messages.

## Output Format

The script outputs labeled sections:

```
============================================================
PR Context: feature-branch -> main
============================================================

Commits: 5
Merge base: abc1234 previous commit message

--- COMMIT LOG ---
(short log)

--- COMMIT MESSAGES (full) ---
(full messages with separators)

--- DIFF STATS ---
(file change summary)

--- DIFF ---
(full diff, truncated if >8000 lines)
```

## Architecture

- `SKILL.md` — This file
- `pr-description` — Executable bash script
