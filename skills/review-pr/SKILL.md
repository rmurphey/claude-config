---
name: review-pr
description: Review a pull request by fetching its diff, reading changed files, and running relevant reviewer agents against them. Produces a structured review with findings organized by severity.
---

# review-pr

Review a pull request using the full suite of reviewer agents.

## How to invoke

```
/review-pr <pr-number-or-url>
```

## Examples

```bash
# Review PR by number (current repo)
/review-pr 42

# Review PR by URL
/review-pr https://github.com/org/repo/pull/42
```

## What You Must Do

### Step 1: Fetch PR context

Run these commands in parallel:

- `gh pr view <number> --json title,body,author,baseRefName,headRefName,files,additions,deletions` — get PR metadata
- `gh pr diff <number>` — get the full diff
- `gh pr checks <number>` — get CI status (if available)
- `gh pr view <number> --json comments,reviews` — get existing review comments

### Step 2: Identify changed files and their types

From the PR metadata, categorize each changed file:

- **Python files** (.py) → queue for python-reviewer
- **React files** (.tsx, .jsx) → queue for react-reviewer
- **TypeScript/JavaScript** (.ts, .js, .mjs, .cjs, non-React) → queue for ts-reviewer
- **Shell scripts** (.sh, .bash, .zsh) → queue for shell-reviewer
- **CSS files** (.css, .scss, .less) → queue for css-reviewer
- **Test files** (test_*, *.test.*, *.spec.*) → queue for test-reviewer
- **Markdown prose** (.md, non-config) → queue for writing-reviewer
- **Security-sensitive files** (auth, session, crypto, etc.) → queue for security-reviewer
- **Data/privacy-sensitive files** (model, schema, logging, etc.) → queue for privacy-reviewer
- **AI-related files** (imports anthropic/openai/langchain) → queue for ai-security-reviewer
- **Dependency files** (package.json, requirements.txt, etc.) → queue for dependency-reviewer

### Step 3: Read changed files

For each changed file in the PR:

1. Check out the PR branch locally if not already: `gh pr checkout <number>`
2. Read the full file (not just the diff) to understand context
3. If this is a test file, also read the code under test

### Step 4: Run reviews

For each file category identified in Step 2, mentally apply the corresponding reviewer agent's checklist. Consolidate findings across all reviewers.

**Do NOT launch separate sub-agents.** Apply the review checklists yourself — you have access to all agent definitions and can read them if needed.

### Step 5: Check for cross-cutting concerns

After reviewing individual files, evaluate the PR as a whole:

- **Blast radius**: how many systems does this change touch?
- **Test coverage**: are all changed code paths tested? Flag any source changes without corresponding test changes.
- **Migration safety**: are there database migrations? Are they reversible?
- **Configuration changes**: do config changes require deployment coordination?
- **Documentation**: are public API changes documented?

### Step 6: Present review

Organize findings into a structured review:

```markdown
## PR Review: #<number> — <title>

### Summary
<1-2 sentence assessment of the PR's quality and readiness>

### Critical (must fix before merge)
- **file:line** — issue description
  - Why: ...
  - Fix: ...

### Warnings (should fix before merge)
- ...

### Suggestions (nice to have)
- ...

### What looks good
<Brief note on what the PR does well — specific, not generic>

### Test coverage assessment
<Are the changes adequately tested? What's missing?>
```

If the PR is clean, say so concisely. Do not manufacture findings.

## Rules

- **Read the full files**, not just the diff — context matters
- **Do not leave review comments on GitHub** unless the user explicitly asks
- **Do not approve or request changes on GitHub** unless the user explicitly asks
- **Focus on substance** — skip style issues that a linter would catch
- **Be specific** — file paths, line numbers, concrete fix suggestions
- **Acknowledge good work** — note what the PR does well, briefly

## Architecture

- `SKILL.md` — This file (instruction-based skill, no executable)
