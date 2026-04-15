# claude-config

A personal [Claude Code](https://docs.claude.com/en/docs/claude-code) configuration — opinionated defaults for code review, test discipline, commit hygiene, and security. Clone it wholesale or copy individual pieces.

## What you get

**15 specialized reviewer agents** that activate automatically based on what you edit — React components, Python scripts, test files, shell scripts, CSS, TypeScript, documentation, dependency manifests, and files with security or privacy implications. Plus on-demand reviewers for defensive design, documentation completeness, and codebase duplication.

**11 slash-command skills** for the most common workflow tasks: `/commit`, `/push`, `/review-pr`, `/pr-description`, `/changelog`, `/secrets-scan`, `/validate-config`, and more.

**9 hooks** that enforce TDD, atomic commits, test integrity, and skill safety — plus advisory checks before pushing or executing Python scripts.

**Global principles** in `CLAUDE.md` covering communication style, error prevention, git discipline, test integrity, and a zero-tolerance list of filler writing phrases.

## Installation

```bash
git clone https://github.com/rmurphey/claude-config.git ~/.claude
```

Paths in `settings.json` resolve via `~`, so they work for any user without rewriting. On first run, `chmod +x` the executable skills if needed:

```bash
find ~/.claude/skills -type f -perm -u+r ! -name "*.md" ! -name "*.py" -exec chmod +x {} +
```

## Agents

Triggered automatically via PostToolUse hooks when matching files are modified. Each agent has a focused checklist and severity-ranked output (Critical / Warning / Suggestion).

| Agent | Fires on | Reviews for |
|---|---|---|
| `python-reviewer` | `.py` files | Type hints, error handling, resource management, Pythonic idioms, security, subprocess safety |
| `react-reviewer` | `.tsx`, `.jsx` | Hooks correctness, rendering/reconciliation, state management, concurrent features, a11y, TS prop types |
| `ts-reviewer` | `.ts`, `.js`, `.mjs`, `.cjs` (non-React) | Type safety, async correctness, error handling, module design, Node.js patterns |
| `shell-reviewer` | `.sh`, `.bash`, `.zsh` | Quoting safety, error handling, portability, variable safety, command injection |
| `css-reviewer` | `.css`, `.scss` | Specificity, responsive coverage, flexbox/grid, animations, design system consistency |
| `test-reviewer` | Test files (any language) | Coverage adequacy vs code under test, assertion quality, isolation, edge cases, flakiness |
| `writing-reviewer` | `.md` prose files | Banned phrases from CLAUDE.md, weak openings, passive voice, filler, paragraph flow |
| `security-reviewer` | Auth/crypto/session/route files | OWASP Top 10 (A01–A10) — injection, broken access control, crypto failures, SSRF, secrets |
| `privacy-reviewer` | Model/schema/logging files | PII in logs, data minimization, sensitive data in errors, retention, third-party sharing |
| `defensive-design-reviewer` | Pre-push advisory + on-demand | Fail-open vs fail-closed, least privilege, defense in depth, blast radius, naive implementations |
| `ai-security-reviewer` | Files importing AI SDKs | OWASP LLM Top 10 — prompt injection, sensitive data in prompts, excessive agency, unbounded consumption |
| `dependency-reviewer` | Manifest/lock files | Supply chain — typosquatting, wide version ranges, install scripts, lock file integrity |
| `observability-reviewer` | Handler/service/route files | Logging, metrics, tracing, error tracking, health checks, structured context |
| `documentation-reviewer` | On-demand | Whether a changeset needs doc updates — missing docstrings, stale READMEs, missing CHANGELOG entries, undocumented env vars |
| `duplication-reviewer` | On-demand | Literal, structural, and concept duplication across the codebase; recommends concrete consolidations |

## Skills

Invocable via slash commands. Most are instruction-based (pure `SKILL.md`); a few include executable scripts.

| Skill | Purpose |
|---|---|
| `/commit` | Groups changes by topic and creates atomic conventional commits. Never amends, never bypasses hooks. |
| `/push` | Branch-aware push with safety checks. Offers to create a draft PR on first push to a new branch. |
| `/review-pr <number>` | Fetches a PR via `gh`, reads changed files, routes each to the relevant reviewer agents, produces a structured review. |
| `/pr-description` | Collects commits and diff against a base branch for PR description authoring. |
| `/changelog [from] [to]` | Generates a changelog grouped by conventional commit prefix between two refs. |
| `/secrets-scan` | Regex and entropy-based scanner for AWS keys, GitHub tokens, Slack tokens, Stripe keys, private keys, connection strings, and generic high-entropy secrets. |
| `/validate-config` | Checks hook script references, skill structure, agent frontmatter, and permission syntax. |
| `/check-prose` | Greps Markdown files for banned phrases defined in CLAUDE.md. Dynamically reads the phrase list at runtime. |
| `/dead-files` | Traces imports from entry points to find unused files. |
| `/md2latex` | Converts Markdown to PDF via Pandoc with list-formatting auto-fix. |
| `/sync-pdfs` | Regenerates stale or missing PDFs in `pdf-output/` directories. |

## Hooks

Hooks fire automatically via Claude Code's hook system. Some block (PreToolUse, exit 2), others advise (exit 0 with `hookSpecificOutput`).

### Blocking hooks (PreToolUse)

- **`enforce-tdd.py`** — Requires a failing test to exist before allowing source file edits. Exempts docs, config, and markup.
- **`check-test-modification.py`** — Blocks suspicious test changes (assertion values flipped without approval, test removals) to prevent auto-fixing tests to pass.
- **`enforce-atomic-commits.py`** — Analyzes staged files and commit message for signs of non-atomic commits (multiple conventional prefixes, unrelated directory groups). User can bypass with "single commit" in the conversation.
- **`reset-tdd-on-commit.py`** — Resets TDD state tracker after a successful commit.
- **`skill-governance.py`** — Governs skill/agent invocations. Blocklist, dangerous-pattern detection (eval, pipe to bash/curl/nc, sudo, command substitution), optional audit logging. Fails closed.
- **`check-webfetch.js`** — Validates WebFetch URLs, warns on excessive `<head>` section size (50KB warn, 100KB fail) to prevent context bloat.

### Advisory hooks (never block)

- **`pre-push-review.py`** — Before `git push`, checks unpushed commits for security/architecture-sensitive filenames. Suggests running the defensive-design-reviewer.
- **`pre-exec-python.py`** — Before running `python3 <script>.py`, scans the script for dangerous patterns (eval, exec, pickle.load, shell=True, mktemp race, verify=False, chmod 777, rmtree). Always exits 0.
- **PostToolUse file-pattern hooks** — 10 hooks registered in `settings.json` that match file types and suggest the appropriate reviewer agent after any Edit or Write.

## How the pieces work together

1. **You edit a file.** A PostToolUse hook detects the file type and injects a suggestion to run the relevant reviewer.
2. **The reviewer agent runs.** It uses `git diff HEAD`, reads modified files in full, applies its checklist, and reports findings by severity with concrete fixes.
3. **You run `/commit`.** The commit skill groups changes by topic, presents a plan for approval, and creates one atomic commit per group. The atomic-commit hook blocks if the grouping mixes topics.
4. **You run `/push`.** Safety checks confirm branch, warn on direct pushes to main/master, and offer to create a draft PR on first push. The pre-push advisory hook flags security-sensitive files in unpushed commits.
5. **You receive a PR to review.** `/review-pr <number>` fetches it, reads changed files, and routes each through the relevant agents.

## Requirements

- **Python 3.9+** and **`pytest`** (`pip3 install pytest`) — for hook and skill test suites
- **`jq`** — used by PostToolUse hooks to parse JSON
- **`git`** — required for most agents and skills
- **`gh`** (GitHub CLI) — required for `/push` auto-PR and `/review-pr`
- **`pandoc`** with LaTeX — required for `/md2latex` and `/sync-pdfs` only
- **`git-filter-repo`** — not required at runtime; mentioned here in case you do similar cleanup

## Testing

```bash
python3 -m pytest hooks/test_*.py skills/secrets-scan/test_*.py -v
```

Currently 136 tests across four suites: skill governance, pre-push review, pre-execution Python review, and secrets scanning.

## Validation

```bash
./skills/validate-config/validate-config
```

Checks that every registered hook script exists, every skill has a `SKILL.md`, every agent has required frontmatter, and every permission entry has valid syntax.

## Customization

- **`CLAUDE.md`** — Edit to match your own communication style, naming conventions, writing standards, and workflow preferences. It's loaded into every conversation automatically.
- **`settings.json`** — Add or remove permission patterns. Register additional hooks. Adjust `effortLevel`.
- **Agents** — Each is a self-contained Markdown file with YAML frontmatter. Edit the checklist sections, tighten the scope in the `description`, or remove agents you don't want.
- **Skills** — Each is a directory under `skills/` with a `SKILL.md`. Instruction-based skills are Markdown only; executable skills include a script.
- **Hooks** — Python scripts in `hooks/` registered in `settings.json`. Blocking hooks exit 2; advisory hooks output JSON via `hookSpecificOutput`.

## Copying individual pieces

Each agent, skill, and hook is self-contained:

- **Agents** — Copy `agents/<name>.md` into your own `~/.claude/agents/`. No registration needed.
- **Skills** — Copy `skills/<name>/` into your own `~/.claude/skills/`. Keep the executable bit on any scripts.
- **Hooks** — Copy `hooks/<name>.py` into your own `~/.claude/hooks/`, then register it in your `settings.json` under `hooks.PreToolUse` or `hooks.PostToolUse` with the appropriate matcher.

See the existing `settings.json` for hook registration patterns.

## License

MIT. See [LICENSE](LICENSE) if present, otherwise treat this as MIT-licensed.
