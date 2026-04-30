# Backlog Format Reference

## File Location

`.claude/BACKLOG.md` in the project root. Git-tracked. Human-editable.

---

## Full Structure

```markdown
# Backlog

<!-- empty-checks: 0 -->

## 🔴 Urgent

## 🟠 High

## 🟡 Normal

- [ ] **WF-001** `[fix]` Fix radar overlay z-index on mobile
  > Overlaps the legend at screens < 768px width.
  > AC: All overlays visible and non-overlapping at 375px. Legend fully readable.

## 🟢 Low

## 💭 Wishlist

## In Progress

## Blocked

## Done

```

---

## Task Entry Format

```
- [STATUS] **WF-NNN** `[TYPE]` Title  _(started: TIMESTAMP)_
  > Context line (one sentence of background)
  > AC: Acceptance criterion 1. Criterion 2.
  > Done: Completion summary (TIMESTAMP)         ← added on completion
  > **Blocker:** Specific question or decision    ← added on block
  > User response: User's reply                  ← added when user unblocks
```

Only the status marker, ID, type, and title are required. Context and AC are strongly recommended for non-trivial tasks.

---

## Status Markers

| Marker | Meaning |
|--------|---------|
| `[ ]` | Pending — eligible to be picked up |
| `[~]` | In-progress — currently being worked |
| `[!]` | Blocked — waiting on human input |
| `[x]` | Done — completed and moved to Done section |

At most one task should be `[~]` at any time.

---

## Type Tags

| Tag | Use for |
|-----|---------|
| `[fix]` | Bug fix, incorrect behavior, broken feature |
| `[feat]` | New user-visible capability |
| `[code]` | Refactor, cleanup, non-user-visible code change |
| `[review]` | Code review of existing code or a PR — Claude does not write code, only reviews |
| `[test]` | Add or fix tests |
| `[docs]` | Documentation, comments, README |
| `[chore]` | Dependency update, config, CI, tooling |
| `[research]` | Investigation, spike, write up findings |

---

## Priority Sections

Tasks live under one of four priority sections. Place each new task under the correct header. During execution, Claude processes 🔴 before 🟠 before 🟡 before 🟢.

- `## 🔴 Urgent` — blocking, time-sensitive, production issue
- `## 🟠 High` — important, should be done soon
- `## 🟡 Normal` — default priority for most tasks
- `## 🟢 Low` — nice to have, no deadline

---

## Wishlist Tier

The `## 💭 Wishlist` section holds items that aren't ripe for execution — ideas, possibilities, things someone might want to do later. Wishlist items have **no priority tier**.

- Execute mode does **not** pick from Wishlist.
- List mode does **not** show Wishlist (use the "show wishlist" trigger instead).
- Status Report adds a single count line below its table: `Wishlist (not yet ripe): N`.

To move an item out of Wishlist into the operational backlog, use a "promote" trigger: `promote WF-NNN [to <tier>]`. The target tier is parsed from the phrasing — "urgent" / "high" / "normal" / "low" (or the matching emoji) — and defaults to 🟡 Normal if unspecified.

---

## ID Assignment

IDs are sequential integers padded to 3 digits: `WF-001`, `WF-002`, etc. Find the highest existing ID across all sections (including Done) and increment. IDs are never reused.

---

## The `<!-- empty-checks: N -->` Comment

Tracks consecutive loop iterations where the queue was empty. The Execute mode uses this to decide when to stop polling. Always update it in place — do not add a second copy.

---

## Done Section Management

The Done section holds completed tasks, newest first. Keep the last 20. When adding a 21st, remove the oldest entry. Format:

```
- [x] **WF-004** `[fix]` Correct typo in forecast.js
  > Done: Corrected "temperture" → "temperature" in forecast.js:42 (2026-04-26T11:30:00Z, deadbee)
```

The `deadbee` is the short SHA of the work commit produced in Step 6 — captured by Execute mode and appended to the Done line, comma-separated after the timestamp. If the task closed without a work commit (rare; typically a `[review]` task that produced no code), the SHA is omitted and only the timestamp appears.

---

## Example: Each Task Type

### `[fix]` — Bug fix
```
- [ ] **WF-010** `[fix]` Wet bulb alert not dismissing on mobile
  > Dismiss button renders but tap doesn't fire. Reported on iOS Safari 17.
  > AC: Tap on dismiss button closes the alert on iOS Safari 17 and Android Chrome.
```

### `[feat]` — New feature
```
- [ ] **WF-011** `[feat]` Add 7-day precipitation probability chart
  > Users want to see rain chance across the forecast period, not just today.
  > AC: Chart appears in forecast tab. Uses Open-Meteo precipitation_probability. Matches trendCharts visual style.
```

### `[code]` — Refactor
```
- [ ] **WF-012** `[code]` Extract weather icon logic into shared util
  > Icon selection repeated in hero.js, forecast.js, and detailTabs.js.
  > AC: Single getWeatherIcon() function in constants.js. All three callers use it. Tests pass.
```

### `[review]` — Code review
```
- [ ] **WF-013** `[review]` Review new chat.js changes for security issues
  > Recent PR added user-supplied text sent directly to the AI endpoint.
  > AC: Security-reviewer findings documented. Any critical issues flagged before merge.
```

### `[test]` — Tests
```
- [ ] **WF-014** `[test]` Add tests for climateComparison handler
  > server/handlers/climateComparison.js has no tests.
  > AC: Unit tests cover happy path, empty data response, and fetch error. All pass.
```

### `[chore]` — Maintenance
```
- [ ] **WF-015** `[chore]` Update anthropic SDK to latest
  > package.json shows @anthropic-ai/sdk ^0.20.0. Latest is 0.26.0.
  > AC: Updated in package.json, npm install clean, existing tests pass, no API breakage.
```

### `[research]` — Investigation
```
- [ ] **WF-016** `[research]` Investigate CPC drought GeoJSON availability
  > Current USDM proxy may have a better source. Investigate alternatives.
  > AC: Write up findings in a comment on this task. Include URLs, update frequency, format.
```

### With `[push]` flag
```
- [ ] **WF-017** `[feat]` Deploy new radar overlay to production [push]
  > AC: Overlay renders in production. No console errors.
```

The `[push]` flag in the title line tells the Execute loop to request human approval before invoking `/push` after committing.
