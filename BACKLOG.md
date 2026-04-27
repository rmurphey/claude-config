# Backlog

<!-- empty-checks: 0 -->

## 🔴 Urgent

## 🟠 High

- [ ] **WF-003** `[docs]` Make BACKLOG.md self-documenting for cold readers
  > Outsiders opening BACKLOG.md don't know what 🟠 means, what `[~]` means, or what `[code]` is for. Add a legend so the file reads cold without anyone chasing down references/.
  > AC: Seeded template includes a brief legend after the title — priority emojis, status markers, type tags, all explained inline in under ~15 lines. Update lands in `init-backlog.sh`. Existing backlogs are not touched (idempotency preserved). references/backlog-format.md remains the deeper spec.

- [ ] **WF-008** `[docs]` Document the "evaluate-then-write" learnings rule in skill docs (not memory)
  > User principle: durable knowledge about how the workflow operates lives in git-tracked docs, not in `~/.claude/projects/.../memory/`. Memory is per-user, hidden, and not portable; docs are visible to collaborators, versioned, and survive session/machine changes. The rule applies to every cycle: evaluate for a non-obvious lesson, write it as documentation when one exists, skip when it doesn't.
  > AC: A new step or subsection lands in `~/.claude/skills/workflow/SKILL.md` (or `references/execution-guide.md`) describing the cycle-end evaluation, what counts as memory-worthy ("would future-me, in a different session, want this fact and not be able to derive it from code, git log, or CLAUDE.md?"), and where each kind of lesson goes (skill SKILL.md / references for behavior, project-level CLAUDE.md for project facts, never per-user memory). The "what NOT to save" list from CLAUDE.md is referenced or restated. Future cycles must follow this rule.

## 🟡 Normal

- [~] **WF-004** `[feat]` Add a Wishlist tier to BACKLOG.md _(started: 2026-04-27 13:45)_
  > Items not yet ripe for execution don't fit the four operational tiers. Without a holding pen, they pollute 🟢 Low or live as floating notes. A dedicated tier keeps them in the same source of truth without competing with active work.
  > AC: New section between 🟢 Low and "In Progress", e.g. `## 💭 Wishlist`. Execute mode skips this tier when picking the next task. "add to wishlist" / "promote to backlog" trigger phrases route correctly. Documented in references/backlog-format.md and the WF-003 legend.

- [ ] **WF-005** `[feat]` Append commit short SHA to Done entries on task completion
  > Today the Done line records what changed but not where to look in git. Adding the short SHA gives collaborators a one-click trace from a BACKLOG entry to its commit.
  > AC: Execute mode captures the short SHA produced by `/commit` and appends it to the `> Done: ...` line, e.g. `> Done: ... (2026-04-26 14:02, deadbee)`. Tasks that close without a commit (rare) get no SHA. Surfaces in Status Report mode (WF-002).

## 🟢 Low

- [ ] **WF-006** `[feat]` Flag stale `[~]` tasks in Status mode
  > A task left in `[~]` for days is usually forgotten in-progress work, not active work. Surface it so the user can decide whether to resume, block, or cancel.
  > AC: Status mode marks any `[~]` older than a threshold (default 7 days, single named constant) with a `⏳ stale` indicator. Status Report mode (WF-002) surfaces stale items as a separate sub-list.

- [ ] **WF-007** `[feat]` Handle orphan `[~]` tasks on Execute pickup
  > If a prior session crashed, was interrupted, or otherwise left a `[~]` claim without finishing, today's Execute Step 2 silently skips it (it's not `[ ]` and not `[!]`). The task gets stuck. Need an explicit policy: detect orphan `[~]` at pickup and choose a safe action.
  > AC: Execute Step 2 detects any `[~]` not started in the current session. Behavior: reset to `[ ]` if no progress evidence in git, OR mark `[!]` with a "session crashed mid-task — verify state and resume" blocker. Choice documented in SKILL.md. Distinct from WF-006 (which only surfaces staleness in Status mode without acting on it).

## In Progress

## Blocked

## Done

- [x] **WF-009** `[feat]` Add branch + worktree creation to /workflow Execute mode
  > Done: Added Per-task Workspace section to SKILL.md, updated Execute Step 2/3/7 for branch+worktree flow, added matching detail to references/execution-guide.md, added `.worktrees/` to .gitignore. Bootstrap commit on main; future tasks branch from main HEAD per the new rule (2026-04-26 19:51)

- [x] **WF-002** `[feat]` Add Status Report mode to /workflow with shareable visual current-state output
  > Done: Added Mode: Status Report to SKILL.md with counts-per-tier table, in-progress and blocked lists, recent-done list. Triggers added to Detecting Intent table and frontmatter description (2026-04-26 19:40)

- [x] **WF-001** `[chore]` Remove the VISION.md feature from the workflow skill
  > Done: Deleted VISION template + local copy, reverted init-backlog.sh and SKILL.md to BACKLOG-only, verified fresh init creates only BACKLOG.md (2026-04-26 19:29)

