---
name: workflow
description: This skill should be used when the user asks to "add to the backlog", "add a task", "queue this", "remember to", "show the backlog", "list tasks", "what's pending", "work on the backlog", "work on next task", "keep going", "what's in progress", "what's blocked", "show blockers", "what's done", "recently completed", "status report", "show progress", "backlog summary", "add to wishlist", "wishlist this", "show wishlist", or "promote to backlog". Manages a project backlog at .claude/BACKLOG.md and executes tasks autonomously — Claude does the work, agents review it, skills handle commits and pushes.
---

# workflow

Manages a project backlog at `.claude/BACKLOG.md` and executes tasks. Claude is the primary executor: it reads the task, assesses complexity, explores the codebase, makes changes, runs tests, and commits. Specialized agents from `~/.claude/agents/` verify work when warranted. Existing skills handle commits, pushes, and PR workflows.

Commits are automatic. Push always requires explicit human approval.

## Initialization

Run `bash ~/.claude/skills/workflow/scripts/init-backlog.sh` before any operation to ensure `.claude/BACKLOG.md` and its structure exist.

Full backlog format: `references/backlog-format.md`.
Execution detail by task type: `references/execution-guide.md`.

---

## Per-task Workspace

Every Execute-mode task runs in its own branch and its own worktree. The split is:

| Where | What lives there |
|-------|-----------------|
| `main` | Authoritative `BACKLOG.md`, **only** as updated by merged task branches. The loop reads `main`'s `BACKLOG.md` to pick the next task. |
| `wf/NNN-slug` (branch) | All commits for the task — code/doc changes plus the `BACKLOG.md` lifecycle updates (`[~]` → `[x]` or `[!]`). |
| `<repo-root>/.worktrees/wf-NNN-slug/` | Working directory for that branch. Steps 4–7 run inside this worktree. |

**Slug.** Lowercase, dash-separated, ~3 words derived from the task title. Example: `wf/009-branch-worktree-setup`.

**Base.** Branches always start from current `main` HEAD at claim time.

**Merge policy.** Branches are **never** auto-merged. The user reviews and merges each branch manually when ready. This extends "never push without approval" to "never integrate without approval."

**Cleanup.** Worktree and branch stay until the user removes them. Not automatic.

**Loop coordination.** Step 2 (Pick next task) skips any task whose `wf/NNN-*` branch already exists — that task is in flight, blocked, or completed-but-unmerged.

---

## Detecting Intent

| User says | Mode |
|-----------|------|
| "add …", "queue …", "remember to …", "backlog this" | **Add** |
| "show backlog", "list tasks", "what's pending" | **List** |
| "work on backlog", "next task", "keep going", bare `/workflow` | **Execute** |
| "what's in progress", "what's blocked", "show blockers" | **Status** |
| "what's done", "recently completed", "show finished" | **Done** |
| "status report", "show progress", "backlog summary" | **Status Report** |
| "add to wishlist", "wishlist this" | **Wishlist** (add) |
| "show wishlist", "what's in the wishlist" | **Wishlist** (show) |
| "promote WF-NNN", "promote to backlog", "move WF-NNN to backlog" | **Wishlist** (promote) |

---

## Mode: Add

1. Run `bash ~/.claude/skills/workflow/scripts/init-backlog.sh`.
2. Assign next ID: find highest existing `WF-NNN` in `BACKLOG.md`, increment by 1. Start at `WF-001` if none exist.
3. Infer priority from language: "urgent"/"asap"/"critical" → 🔴, "soon"/"important" → 🟠, default → 🟡, "someday"/"low" → 🟢.
4. Infer type tag from description: bug/broken/wrong → `[fix]`, new capability → `[feat]`, cleanup/refactor → `[code]`, testing → `[test]`, docs → `[docs]`, dependency/config → `[chore]`, investigation → `[research]`, PR review → `[review]`.
5. If acceptance criteria are clear from context, include them. If genuinely unclear and the task is non-trivial, ask one focused question: "What does done look like?"
6. Append the task to the correct priority section in `BACKLOG.md` using the format from `references/backlog-format.md`.
7. Confirm: "Added **WF-NNN** — title."

---

## Mode: List

Read `BACKLOG.md`. Display pending (`[ ]`) tasks grouped by priority tier (🔴 → 🟠 → 🟡 → 🟢). For each: ID, type tag, title, one-line context summary. The `## 💭 Wishlist` tier is intentionally hidden — surface it via "show wishlist" instead. Do not begin execution.

---

## Mode: Status

Read `BACKLOG.md`. Show:
- In-progress (`[~]`): ID, title, when started
- Blocked (`[!]`): ID, title, blocker description

For each blocked task, offer via `AskUserQuestion`:
- **Provide answer** — append as `> User response: …` and change `[!]` back to `[ ]`
- **Cancel** — change to `[x]`, append `> Cancelled by user`, move to Done section
- **Leave blocked** — no change

---

## Mode: Done

Read `BACKLOG.md`. Show the Done section — last 20 entries, newest first. Display: ID, title, completion summary line.

---

## Mode: Status Report

Read `BACKLOG.md`. Produce a single markdown digest suitable for sharing in a doc, issue, or chat. Do not modify the backlog.

Output, in order:

**Counts by tier:**

| Tier | Pending | In progress | Blocked |
|------|---------|-------------|---------|
| 🔴 Urgent | N | N | N |
| 🟠 High | N | N | N |
| 🟡 Normal | N | N | N |
| 🟢 Low | N | N | N |
| **Total** | N | N | N |

**In progress** — for each `[~]` task, one line: `**WF-NNN** title — _started: TIMESTAMP_`. If none: `_None._`

**Blocked** — for each `[!]` task, one line: `**WF-NNN** title — Blocker: <one-line summary>`. If none: `_None._`

**Recently done** — last 5 from the Done section, newest first: `**WF-NNN** title — <one-line Done summary>`. If fewer than 5 exist, show all.

**Wishlist** — single line below the table: `Wishlist (not yet ripe): N`, where N is the count of items in `## 💭 Wishlist`. Omit the line if N is 0.

The digest is plain markdown — copy-pasteable into a PR description, issue, or chat. No interactive prompts in this mode.

---

## Mode: Wishlist

Three sub-actions, dispatched by the user's phrasing.

### Add to wishlist
Triggers: "add to wishlist X", "wishlist this", "wishlist X"

1. Run `bash ~/.claude/skills/workflow/scripts/init-backlog.sh`.
2. Assign next ID (same logic as Add mode).
3. Append the item to the `## 💭 Wishlist` section in `BACKLOG.md`. No priority tier inferred — wishlist items don't have one.
4. Confirm: "Added **WF-NNN** to wishlist — title."

### Show wishlist
Triggers: "show wishlist", "what's in the wishlist"

Read `BACKLOG.md`. Display items in the `## 💭 Wishlist` section. ID, type tag, title, one-line context summary.

### Promote
Triggers: "promote WF-NNN", "promote WF-NNN to <tier>", "move WF-NNN to backlog"

1. Read `BACKLOG.md`. Find the item in `## 💭 Wishlist`.
2. Parse target tier from the user's phrasing — look for "urgent" / "high" / "normal" / "low" (or 🔴 / 🟠 / 🟡 / 🟢). Default to 🟡 Normal if unspecified.
3. Move the entry from Wishlist to the chosen tier section.
4. Confirm: "Promoted **WF-NNN** to <tier>."

The `## 💭 Wishlist` tier is **not** picked up by Execute mode and **not** shown by List mode. Status Report mode surfaces a single count line below its main table.

---

## Mode: Execute

The core loop. Process one task at a time until the backlog is clear.

### Step 1 — Initialize

Run `bash ~/.claude/skills/workflow/scripts/init-backlog.sh`.

Read the `<!-- empty-checks: N -->` comment from `BACKLOG.md` to restore the empty-queue counter.

### Step 2 — Pick next task

Read `BACKLOG.md` (on `main`). Find the first `[ ]` task in priority order: 🔴 → 🟠 → 🟡 → 🟢. Skip `[!]` blocked tasks. Skip any task in the `## 💭 Wishlist` tier — those must be promoted explicitly first. Skip any task whose `wf/NNN-*` branch already exists (`git branch --list 'wf/NNN-*'` returns a hit) — that task's work is on a branch awaiting merge.

**If no pending tasks:**
- Increment the empty-check counter. Update `<!-- empty-checks: N -->` in `BACKLOG.md`.
- Counter < 3: `ScheduleWakeup` with `delaySeconds: 180`, `reason: "polling for new backlog tasks"`, `prompt: "<<autonomous-loop-dynamic>>"`.
- Counter ≥ 3: Report "Backlog is clear — no new tasks in 3 checks." Reset counter to 0. Stop.

**If a pending task exists:** Reset `<!-- empty-checks: 0 -->`. Proceed.

### Step 3 — Claim the task

1. Derive the slug: lowercase, dash-separated, ~3 words from the task title (skip articles).
2. From `main` at the repo root, create the branch and worktree:
   ```bash
   git branch wf/NNN-slug main
   git worktree add ./.worktrees/wf-NNN-slug wf/NNN-slug
   ```
   If the branch already exists, abort with a clear error — do not auto-recover (orphan recovery is WF-007's territory).
3. Change directory into the worktree. **All subsequent steps (4–7) run there.**
4. In the worktree's `BACKLOG.md`, change the task's `[ ]` to `[~]` and append ` _(started: TIMESTAMP)_` on the title line. Don't commit yet — Step 6's `/commit` will pick it up alongside the work.

### Step 4 — Assess complexity

Read the full task entry. Estimate complexity based on signals in `references/execution-guide.md`:

| Complexity | Signals |
|------------|---------|
| **Trivial** | Typo, rename, single constant, CSS value, one-line config |
| **Simple** | Single bug fix, small handler, one-file feature |
| **Medium** | Multi-file feature, new component, refactor |
| **Complex** | New subsystem, architectural change, security-sensitive, major refactor |

If acceptance criteria are missing and cannot be inferred: go directly to Step 7 (Block).

### Step 5 — Execute the work

See `references/execution-guide.md` for full detail. Summary by complexity:

**Trivial**: Edit the file. Run tests only if the project has a fast test suite (`npm test` or equivalent). Proceed to Step 6.

**Simple**: Explore the relevant files first (understand existing patterns). Make the change. Run tests. Fix any failures caused by the change. Proceed to Step 6.

**Medium**: Explore the relevant area of the codebase. Understand conventions and data flow before writing. Make the changes across all affected files. Run the full test suite. Proceed to Step 6.

**Complex**: Spawn a `Plan` agent with the task description and codebase context to design the approach before writing code. Execute that plan. Run tests. Proceed to Step 6.

**`[review]` tasks**: Do not write code. Identify the files/PR in scope, spawn the appropriate reviewer agent(s), compile findings into a summary, report to the user.

**If three consecutive attempts fail** (track with a retry note in the task entry): go to Step 7 (Block).

### Step 6 — Verify and commit

Verify each acceptance criterion is met. Do not mark done if any criterion is unmet.

Invoke the `/secrets-scan` skill before committing if the task touched config, environment handling, or API integrations.

Invoke the `/commit` skill. It handles staging, conventional messages, and hooks. Never bypass hooks.

**After committing — agent review:**
Determine which reviewers to invoke based on what files changed. See agent selection table in `references/execution-guide.md`. Pass the task description, acceptance criteria, and relevant file paths in the agent prompt. If a reviewer surfaces a critical finding, fix it and commit again before marking the task done.

**Push check:**
If the task entry contains `[push]` or the user has previously indicated this task should be pushed: send `PushNotification` "WF-NNN ready to push — approve?" and use `AskUserQuestion` to get approval before invoking `/push`.

### Step 7 — Update backlog

(Still in the worktree, on the task's branch.)

**On success:**
- Change `[~]` to `[x]` on the task line.
- Append below the task: `> Done: <one-sentence summary of what changed> (TIMESTAMP)`
- Move the completed entry to the `## Done` section (prepend; keep last 20 only).
- Reset empty-checks counter.
- Commit on the branch: `git add BACKLOG.md && git commit -m "chore: WF-NNN done"`.
- The branch sits awaiting user merge. The worktree stays.
- Run the cycle-learning check (see § Cycle Learning).

**On block:**
- Change `[~]` to `[!]` on the task line.
- Append: `> **Blocker:** <specific description of what's needed — a question, a decision, missing information>`
- Commit on the branch: `git add BACKLOG.md && git commit -m "chore: WF-NNN blocked"`.
- Send `PushNotification`: "WF-NNN blocked: <one-line summary>"
- Use `AskUserQuestion` if in-session.
- The branch and worktree stay until the task is unblocked or cancelled.

### Step 8 — Loop

`ScheduleWakeup` with `delaySeconds: 60`, `reason: "picking next backlog task"`, `prompt: "<<autonomous-loop-dynamic>>"`.

---

## Cycle Learning

After every task closes (Step 7), evaluate whether the cycle produced a non-obvious lesson that future sessions would want.

**The filter question:** *"Would future-me, in a different session, want this fact and not be able to derive it from code, git log, or CLAUDE.md?"*

If **no** — most cycles end here. Move on. The work is in the commits; the context is in the commit message.

If **yes** — document it where it'll be found:

| Kind of lesson | Goes in |
|----------------|---------|
| User correction or surprising preference about how I should work | `~/.claude/CLAUDE.md` (global) or the relevant skill's `SKILL.md` (skill-scoped) |
| Project-specific decision/constraint that won't be visible from inspection | Project-level `CLAUDE.md` or notes file at the project root |
| Skill internals, gotchas, or behavior rules | The skill's `SKILL.md` or `references/` files |
| Pointer to an external system (dashboard, ticket project, runbook) | Project-level docs |

**Never use per-user memory** (`~/.claude/projects/.../memory/`). Memory is hidden from collaborators, not portable across machines, and not git-tracked. Documentation is.

**Don't write a "lesson" for** (per CLAUDE.md's "what NOT to save" list):
- Files touched, agents invoked, time taken — derivable from `git log`
- Fix recipes — the fix is in the code; the why is in the commit message
- Conventions or architecture — derivable from current state
- Anything already in CLAUDE.md
- Ephemeral task or session state

This filter keeps growth bounded by relevance, not by activity.

---

## Rules

- Never push without explicit human approval.
- Never auto-merge a task branch — user merges manually.
- Never write workflow learnings to per-user memory; document them in skill or project files instead. (See § Cycle Learning.)
- Never mark `[x]` before verifying all acceptance criteria.
- Never bypass `/commit` hooks.
- Never guess when acceptance criteria are missing — block and ask.
- One task in `[~]` at a time.
- Always run tests after code changes, even for trivial tasks if a test suite exists.

---

## Additional Resources

- **`references/backlog-format.md`** — BACKLOG.md full format spec, type tags, examples
- **`references/execution-guide.md`** — complexity rubric, execution paths, agent + skill selection tables, retry handling
- **`scripts/init-backlog.sh`** — creates `.claude/BACKLOG.md` with correct structure
