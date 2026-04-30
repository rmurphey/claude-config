# Backlog

<!-- empty-checks: 0 -->

## 🔴 Urgent

## 🟠 High

## 🟡 Normal

## 🟢 Low

## In Progress

## Blocked

## Done

- [x] **WF-007** `[feat]` Handle orphan `[~]` tasks on Execute pickup
  > Done: Step 2 now does orphan recovery — empty-orphan branches are deleted (task re-enters queue), commit-bearing orphans become [!] on the branch with a "session crashed mid-task" blocker plus PushNotification. Step 3 hardened to require repo-root paths for worktree creation (2026-04-27 14:08, 0d3c9c8)

- [x] **WF-006** `[feat]` Flag stale `[~]` tasks in Status mode
  > Done: Added STALE_THRESHOLD_DAYS = 7 named once in Mode: Status; Status mode prefixes stale [~] with ⏳ stale —; Status Report adds a Stale in progress sub-list. Surface only — no interactive resolution (WF-007 territory) (2026-04-27 14:02, b7a099e)

- [x] **WF-005** `[feat]` Append commit short SHA to Done entries on task completion
  > Done: Step 7 now captures `git rev-parse --short HEAD` and appends it to the Done line after the timestamp; format documented in references/backlog-format.md (2026-04-27 13:55, db2b67b)

- [x] **WF-004** `[feat]` Add a Wishlist tier to BACKLOG.md
  > Done: New ## 💭 Wishlist section in seeded template, new Mode: Wishlist (add/show/promote with tier-from-phrasing, default 🟡 Normal), Execute/List/Status Report updated, references/backlog-format.md documents the new tier and promote semantics. Legend update deferred (cross-branch dependency on WF-003) (2026-04-27 13:48)

- [x] **WF-008** `[docs]` Document the "evaluate-then-write" learnings rule in skill docs (not memory)
  > Done: Added a Cycle Learning section to SKILL.md with the filter question, a kind→home table, the "never per-user memory" rule, and a re-statement of the "what NOT to save" list from CLAUDE.md. Step 7 references it; Rules section adds the "no per-user memory" rule (2026-04-26 20:01)

- [x] **WF-003** `[docs]` Make BACKLOG.md self-documenting for cold readers
  > Done: Added a two-line Legend (priority/status/type tags + lifecycle summary) to the heredoc in init-backlog.sh. Cold readers can grasp the file without chasing references/. Verified idempotency on existing backlogs (2026-04-26 19:56)

- [x] **WF-009** `[feat]` Add branch + worktree creation to /workflow Execute mode
  > Done: Added Per-task Workspace section to SKILL.md, updated Execute Step 2/3/7 for branch+worktree flow, added matching detail to references/execution-guide.md, added `.worktrees/` to .gitignore. Bootstrap commit on main; future tasks branch from main HEAD per the new rule (2026-04-26 19:51)

- [x] **WF-002** `[feat]` Add Status Report mode to /workflow with shareable visual current-state output
  > Done: Added Mode: Status Report to SKILL.md with counts-per-tier table, in-progress and blocked lists, recent-done list. Triggers added to Detecting Intent table and frontmatter description (2026-04-26 19:40)

- [x] **WF-001** `[chore]` Remove the VISION.md feature from the workflow skill
  > Done: Deleted VISION template + local copy, reverted init-backlog.sh and SKILL.md to BACKLOG-only, verified fresh init creates only BACKLOG.md (2026-04-26 19:29)

