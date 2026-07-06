---
name: audience-review
description: Review a draft from the target reader's perspective. Checks whether the piece makes the reader feel seen or scolded, flags power dynamic issues, and evaluates shareability.
user-invocable: true
---

# Audience Review Skill

Review a draft from the target reader's perspective using the audience-reviewer agent.

## Steps

1. **Resolve the draft file**
   - If the invocation names a file, use it.
   - Otherwise, find the most recently modified `.md` file in the current directory tree and confirm it with the author before proceeding.

2. **Ask about target audience**
   - Ask the author who the intended reader is (e.g. "VP Eng at a Series C," "Staff engineer weighing a move into management," "Engineering leader skeptical of AI hype").
   - Do not guess — the review is only useful when read as the right person.

3. **Launch audience-reviewer agent**
   - Pass the draft file path and the audience description.
   - The agent reviews entirely from the reader's perspective.

4. **Present findings**
   - Show the agent's full review to the author.
   - The review covers: felt sense, power dynamics, recognition moments, and shareability.
