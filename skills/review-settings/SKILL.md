---
name: review-settings
description: Review the allowed-commands list in a directory's Claude Code settings (settings.json and settings.local.json), identify entries that could reasonably be consolidated into fewer, broader patterns, and offer to write the change as a diff. Use when the permissions.allow list has grown long or repetitive and you want to tidy it up.
---

# review-settings

Reviews the `permissions.allow` list in a project's Claude Code settings and finds
commands that could reasonably be consolidated. Recommends changes; only edits the
files if the user asks for the diff.

## How to invoke

```
/review-settings [directory]
```

If no directory is given, defaults to the current working directory. The skill reads
`.claude/settings.json` and `.claude/settings.local.json` under it.

## What it does

1. **Extract and group (deterministic).** Run the bundled script:

   ```
   .claude/skills/review-settings/review-settings [directory]
   ```

   It locates the two settings files, parses them, and groups every `permissions.allow`
   entry by tool + leading token (e.g. all `Bash(git ...)` entries land in one group).
   It emits JSON with `allow` (the raw lists) and `consolidation_candidates` (only the
   groups with more than one entry — these are what's worth looking at).

2. **Judge which groups to consolidate.** For each candidate group, decide whether
   collapsing it is actually a good idea. Consolidate when the entries are clearly
   variants of the same command family the user has already blessed:
   - Several narrow prefixes of one subcommand set → one broader pattern, e.g.
     `Bash(git add:*)`, `Bash(git status:*)`, `Bash(git commit:*)` → `Bash(git:*)`.
   - A broad entry already present that makes narrower siblings redundant, e.g. a
     `Bash(git *)` next to specific `Bash(git add:*)` entries — drop the redundant ones.
   - Repeated `Edit(...)`/`Read(...)` globs under one parent dir → a single glob.

   Do **not** consolidate when it would widen access in a way the user probably didn't
   intend — e.g. collapsing `Bash(npm run:*)` and `Bash(npm install:*)` into `Bash(npm:*)`
   also permits `npm publish`, `npm config`, etc. Call that out as a tradeoff rather than
   silently broadening. When a consolidation trades tighter scope for a shorter list,
   say so and let the user choose.

3. **Present recommendations.** For each recommended consolidation, show the entries
   being replaced, the single entry replacing them, and one line on what the change
   widens or narrows. Group by "clear win" (pure redundancy / same scope) vs
   "tradeoff" (shorter but broader). Skip groups where consolidation isn't worth it and
   note why briefly.

4. **Offer the diff.** Ask whether to apply the recommended consolidations. Only if the
   user agrees, edit the settings file(s) — remove the replaced entries, add the
   consolidated ones, preserve ordering and formatting, and keep entries from
   `settings.json` vs `settings.local.json` in their own files. Show the diff.

## Scope

This skill only looks at `permissions.allow` consolidation. It does not audit for safety,
validate hooks, or check structure — `/validate-config` covers structural integrity.

## Architecture

- `SKILL.md` — this file
- `review-settings` — executable Python script: locate, parse, group. No judgment, no writes.
