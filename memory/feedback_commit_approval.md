---
name: commit-approval-preference
description: User prefers no confirmation prompt for obvious single-topic commits; only ask when proposing multiple commits
type: feedback
---

Single-commit changes should proceed without asking for approval. Only present a commit plan and wait for approval when proposing multiple commits across varied functionality.

**Why:** The user trusts the conventional-commit prefix and the enforce-atomic-commits hook to catch mistakes. Asking "proceed?" on every trivial commit wastes time.

**How to apply:** When `/commit` determines all changes are one topic, just create the commit and report results. When changes need to be split into multiple commits, always present the plan and wait.
