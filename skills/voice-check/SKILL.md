---
name: voice-check
description: Check whether a piece of prose sounds like Rebecca's authentic writing voice. Runs the voice-authenticator agent against the target Markdown file (or the most recently modified .md if none is given), using the canonical voice model at ~/.claude/voice/STYLEGUIDE.md. Use when the author asks "does this sound like me?", before publishing a draft, or to vet AI-generated prose for voice consistency. Complements /check-prose (banned phrases) and the writing-reviewer agent (mechanical structure) by checking the positive voice signature, not just flaws.
---

# voice-check

Reviews prose against Rebecca's authentic voice and flags passages that don't ring true.

## Steps

1. **Resolve the target file**
   - If the invocation names a file, use it.
   - Otherwise, find the most recently modified `.md` file in the current directory tree and confirm it with the author before proceeding.

2. **Run the voice-authenticator agent**
   - Launch the `voice-authenticator` agent on the target file.
   - The agent reads `~/.claude/voice/STYLEGUIDE.md` (canonical voice model) and `~/.claude/voice/bio.md` (author identity), then flags mismatches inline with `[TODO: VOICE - ...]` markers.

3. **Present the agent's review verbatim**
   - Show the inline-marked content and the Voice Review Summary (overall assessment, patterns noticed, strongest sections, priority fixes).
   - Do not rewrite the prose yourself unless the author asks — the markers are for the author to address.

## Notes

- This is a *positive* voice check. For mechanical flaws (banned phrases, weak openings, passive voice density) use `/check-prose` or the `writing-reviewer` agent.
- The voice model lives in `~/.claude/voice/`, copied from `~/personal/substack` (the source of truth). If the voice guide there changes, re-copy `STYLEGUIDE.md` and `bio.md`.
- Only the professional register is loaded here. The political/civic (Approximately Perfect) voice is a separate guide in the substack repo — pull it in if a task needs it.
