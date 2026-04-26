# Execution Guide

Detailed reference for task assessment, execution approach by complexity and type, agent/skill selection, and retry handling.

---

## Per-task Workspace

See SKILL.md "Per-task Workspace" for the full convention. Operational details:

**Slug derivation**: lowercase the title; drop articles ("a", "the", "to"); replace runs of whitespace with a single dash; truncate to ~3 meaningful words. Example: "Add Status Report mode to /workflow with shareable visual current-state output" → `add-status-report-mode`.

**Branch and worktree at claim**:
```bash
git branch wf/NNN-slug main
git worktree add ./.worktrees/wf-NNN-slug wf/NNN-slug
cd ./.worktrees/wf-NNN-slug
```

**Branch name collisions**: if `wf/NNN-slug` already exists, abort with a clear error — do not auto-recover. Orphan recovery is WF-007's territory.

**Reading BACKLOG.md authoritatively**: Step 2 reads `main`'s working tree `BACKLOG.md` to pick the next task. The pick must skip any task whose `wf/NNN-*` branch already exists (in flight, blocked, or completed-but-unmerged).

**Done commit**: Step 7 commits the BACKLOG.md `[x]` update on the task's branch. The branch is left for the user to merge — no auto-merge to `main`.

---

## Complexity Assessment

Read the full task entry — title, context, acceptance criteria — before assigning complexity. When in doubt, go one level up (safer to over-invest than under-execute).

| Complexity | Signals | Typical examples |
|------------|---------|-----------------|
| **Trivial** | Single file, no logic change, purely textual or cosmetic | Fix a typo, rename a variable, change a color constant, update a comment, bump a version string |
| **Simple** | 1–2 files, clear change, contained logic | Fix a broken conditional, add a missing null check, add a single API field to a response, write a missing test |
| **Medium** | 3+ files, new behavior, follows existing patterns | New chart component, new server handler, refactoring a module, adding a feature flag |
| **Complex** | New subsystem, cross-cutting concern, security-sensitive, significant architecture | New auth layer, new data pipeline, replacing a third-party integration, major performance work |

---

## Execution Path by Complexity

### Trivial
1. Make the change directly — no exploration needed.
2. Run tests only if the project has a fast test runner (`npm test`, `vitest run`). Skip if the only available suite takes > 30s and the change is purely textual.
3. Invoke `/commit`.
4. No reviewer needed.

### Simple
1. Read the file(s) the task references. Understand the surrounding code before touching anything.
2. Make the change.
3. Run the test suite. If tests fail and the failure is related to the change, fix it. If the failure is pre-existing and unrelated, note it in the task entry and proceed.
4. Invoke `/commit`.
5. Invoke a reviewer only if the change touches a sensitive area (see agent selection table below).

### Medium
1. Explore the relevant area of the codebase: read the entry point, trace data flow, read related components/handlers, understand naming and structural conventions.
2. Design the change mentally before writing. Identify all files that need to change.
3. Make changes incrementally — complete one file before moving to the next.
4. Run the full test suite. Fix test failures caused by the change.
5. Invoke `/commit`.
6. Invoke type-appropriate reviewer(s) based on file types touched.

### Complex
1. Spawn a `Plan` subagent with `subagent_type: "Plan"`. Pass: task title, acceptance criteria, and a summary of the relevant codebase area (file paths, key functions, existing patterns). Ask the agent to return a step-by-step implementation plan with file paths and key decisions.
2. Read the plan. If it surfaces a real architectural tradeoff the user should weigh, block the task (`[!]`) and surface the question — do not choose on the user's behalf.
3. Execute the plan.
4. Run the full test suite. Fix failures caused by the change.
5. Invoke `/secrets-scan` if the change touches config, env vars, or API credentials.
6. Invoke `/commit`.
7. Invoke all applicable reviewers from the agent selection table.
8. If the task has `[push]` in its title: request human approval before invoking `/push`.

---

## Execution by Task Type

### `[fix]` — Bug fix
- Reproduce the bug first (read relevant code, understand the failure mode).
- Fix the root cause, not just the symptom.
- Add a regression test if none exists.
- Verify the fix against the acceptance criteria before committing.

### `[feat]` — New feature
- Understand how similar features are implemented in the codebase (use existing patterns).
- Write tests alongside the implementation (TDD where practical).
- Ensure the feature is accessible and handles edge cases (empty state, errors, mobile).

### `[code]` — Refactor / cleanup
- Understand all call sites before changing any signatures.
- Make the refactor atomic — don't mix refactor with behavior changes.
- Verify tests still pass after refactor; tests should not need substantive changes.

### `[review]` — Code review
- Do not write code. Only analyze.
- Identify the files or PR scope from the task description.
- Spawn the appropriate agent(s) from the agent selection table.
- Compile findings by severity: critical (must fix), warning (should fix), info (consider).
- Report findings clearly. Mark the task done after reporting — findings are the deliverable.

### `[test]` — Write tests
- Run the existing suite first to confirm baseline.
- Write tests that cover: happy path, edge cases named in the task, error handling.
- Do not change production code to make tests pass — that signals a design problem; block and flag it.
- Invoke `/test-reviewer` agent after writing tests.

### `[docs]` — Documentation
- Write in the voice and style already present in the file.
- For `[research]` tasks: write findings as a structured comment or a markdown file at the location specified in the task.

### `[chore]` — Maintenance
- For dependency updates: update the version, run `npm install` (or equivalent), run tests, check for breaking API changes in the changelog.
- For config changes: validate the config format before committing.

---

## Agent Selection Table

Invoke reviewers **after** Claude's work is complete and committed. Pass the agent: task description, acceptance criteria, and the specific file paths changed. Incorporate critical findings before marking the task `[x]`.

| What changed | Agent to invoke | When to skip |
|-------------|-----------------|--------------|
| `.ts` or `.tsx` (non-trivial) | `ts-reviewer` | Trivial rename or type alias |
| React components | `react-reviewer` | Trivial CSS/style change only |
| Auth, sessions, tokens, API keys | `security-reviewer` | Never skip if auth is touched |
| AI prompts, LLM tool definitions | `ai-security-reviewer` | Never skip if prompts are touched |
| `.py` files | `python-reviewer` | Trivial change |
| `.sh` or shell scripts | `shell-reviewer` | Never skip |
| `package.json` or lock files | `dependency-reviewer` | Version bump with no API change |
| Logging, metrics, tracing, OTel | `observability-reviewer` | Trivial log message change |
| User data, PII, analytics events | `privacy-reviewer` | Never skip if user data is added |
| New subsystem, trust boundaries | `defensive-design-reviewer` | Simple feature additions |
| `[review]` type tasks | `code-reviewer` + type-specific | — |
| Removing significant code | `duplication-reviewer` | Trivial dead code removal |
| New tests written | `test-reviewer` | — |

Trivial tasks: no reviewer regardless of file type.

---

## Skill Invocation

| When | Skill | Notes |
|------|-------|-------|
| After all code work | `/commit` | Always. Never bypass hooks. |
| Before committing if env/API touched | `/secrets-scan` | Run first; block if findings |
| Task has `[push]` flag | `/push` | Human approval required first |
| Task is a PR review | `/review-pr` | Pass PR number or branch |
| New significant feature | `/pr-description` | Generate before asking user to review |

---

## Retry Handling

Track retry attempts by appending a note to the task entry:
```
> Attempt 1 failed: <error summary> (TIMESTAMP)
> Attempt 2 failed: <error summary> (TIMESTAMP)
```

After 3 failed attempts, stop and block (`[!]`). Do not attempt a fourth time with the same approach. The blocker note should describe specifically what failed and what decision or information is needed.

Between retries on the same task, run the test suite to confirm the baseline. If the baseline has degraded (pre-existing failures increased), note that in the blocker.

---

## Push Approval Flow

When a task has `[push]` in its title or the user requests a push:

1. Complete the task work and commit via `/commit`.
2. Send `PushNotification`: "WF-NNN committed and ready to push. Approve?"
3. Use `AskUserQuestion`:
   - **Approve push** — invoke `/push`
   - **Review first** — stop; user will inspect and decide
   - **Don't push** — leave committed, mark task `[x]` without pushing
4. Record the outcome in the task's Done entry.

Never invoke `/push` without this approval step.

---

## Pre-existing Test Failures

If the test suite has failures before the task change is applied:

1. Note the failing tests by name in the task entry.
2. Proceed with the task.
3. After the change, confirm no new failures were introduced.
4. If new failures appear: fix them if caused by the change; block if they appear unrelated and require investigation.

Do not silently ignore pre-existing failures. Always document them.
