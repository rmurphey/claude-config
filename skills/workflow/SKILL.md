---
name: workflow
description: This skill should be used when the user asks to "add to the backlog", "add a task", "queue this", "remember to", "show the backlog", "list tasks", "what's pending", "work on the backlog", "work on next task", "keep going", "what's in progress", "what's blocked", "show blockers", "what's done", "recently completed", "status report", "show progress", or "backlog summary". Manages a project backlog at .claude/BACKLOG.md and executes tasks autonomously — Claude does the work, agents review it, skills handle commits and pushes.
---

# workflow

Manages a project backlog at `.claude/BACKLOG.md` and executes tasks. Claude is the primary executor: it reads the task, assesses complexity, explores the codebase, makes changes, runs tests, and commits. Specialized agents from `~/.claude/agents/` verify work when warranted. Existing skills handle commits, pushes, and PR workflows.

Commits are automatic. Push always requires explicit human approval.

## Initialization

Run `bash ~/.claude/skills/workflow/scripts/init-backlog.sh` before any operation to ensure `.claude/BACKLOG.md` and its structure exist.

Full backlog format: `references/backlog-format.md`.
Execution detail by task type: `references/execution-guide.md`.

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

Read `BACKLOG.md`. Display pending (`[ ]`) tasks grouped by priority tier (🔴 → 🟠 → 🟡 → 🟢). For each: ID, type tag, title, one-line context summary. Do not begin execution.

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

The digest is plain markdown — copy-pasteable into a PR description, issue, or chat. No interactive prompts in this mode.

---

## Mode: Execute

The core loop. Process one task at a time until the backlog is clear.

### Step 1 — Initialize

Run `bash ~/.claude/skills/workflow/scripts/init-backlog.sh`.

Read the `<!-- empty-checks: N -->` comment from `BACKLOG.md` to restore the empty-queue counter.

### Step 2 — Pick next task

Read `BACKLOG.md`. Find the first `[ ]` task in priority order: 🔴 → 🟠 → 🟡 → 🟢. Skip `[!]` blocked tasks.

**If no pending tasks:**
- Increment the empty-check counter. Update `<!-- empty-checks: N -->` in `BACKLOG.md`.
- Counter < 3: `ScheduleWakeup` with `delaySeconds: 180`, `reason: "polling for new backlog tasks"`, `prompt: "<<autonomous-loop-dynamic>>"`.
- Counter ≥ 3: Report "Backlog is clear — no new tasks in 3 checks." Reset counter to 0. Stop.

**If a pending task exists:** Reset `<!-- empty-checks: 0 -->`. Proceed.

### Step 3 — Claim the task

In `BACKLOG.md`, change the task's `[ ]` to `[~]` and append ` _(started: TIMESTAMP)_` on the title line. Write the file.

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

**On success:**
- Change `[~]` to `[x]` on the task line.
- Append below the task: `> Done: <one-sentence summary of what changed> (TIMESTAMP)`
- Move the completed entry to the `## Done` section (prepend; keep last 20 only).
- Reset empty-checks counter.

**On block:**
- Change `[~]` to `[!]` on the task line.
- Append: `> **Blocker:** <specific description of what's needed — a question, a decision, missing information>`
- Send `PushNotification`: "WF-NNN blocked: <one-line summary>"
- Use `AskUserQuestion` if in-session.

### Step 8 — Loop

`ScheduleWakeup` with `delaySeconds: 60`, `reason: "picking next backlog task"`, `prompt: "<<autonomous-loop-dynamic>>"`.

---

## Rules

- Never push without explicit human approval.
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
