# Report writing guide (data storytelling + copywriting distilled)

Principles distilled from wshobson/agents@data-storytelling and
coreyhaines31/marketingskills@copywriting, adapted for coaching reports. Read this
immediately before writing `assessment.json` prose — it shapes every text field.

## Narrative spine: Setup → Conflict → Resolution

The report is one story: **where the player is** (setup: stage, profile, style),
**what is holding them back** (conflict: the 2–3 weaknesses that gate the next
level), **the path forward** (resolution: development plan). Write every section
conscious of its role in that arc. The reader should finish knowing the ONE thing
to fix first.

## Voice

- **Coach-to-player, direct and warm.** Second person ("your forehand"), active
  voice, plain words. No academic hedging stacks, no marketing hype.
- **Encouraging but honest.** Never inflate the rating to please; never pile on.
  Pair every hard truth with the fix ("contact is late under pace — the spacing
  drill in the plan targets exactly this").
- **Specific beats general, always.** "You hit 11 of 14 backhands cross-court even
  when the line was open (burst 3)" beats "you favor cross-court". Numbers, frame
  references, and timestamps are what make the report feel true.

## Evidence discipline (the trust rule)

- Every claim of fact ties to something checkable: a frame file, a burst sheet,
  a metric from pose/match JSON. Every dimension score's `evidence` field cites
  at least one.
- Present uncertainty as ranges with reasons ("NTRP 3.0–4.0; a single practice
  session can't resolve match temperament"). Confidence language must match
  actual footage coverage.
- What you could NOT see goes in `caveats` — an honest limitations list makes the
  rest of the report more credible, not less.

## Headlines that carry the finding

Section titles and strength/weakness `title` fields state the finding, not the
topic: "Serve: the arm does all the work" beats "Serve analysis". A reader
skimming only headlines should still learn the story.

## Structure mechanics

- Lead each section with its conclusion, then the supporting detail.
- Strengths/weaknesses: 3–5 each, ordered by impact on the next level, each with
  one concrete detail + evidence. Resist listing ten.
- Development plan: max 4 priorities (three is better), each with named drills and
  a **measurable** success metric ("8 of 10 second serves land in with visible
  kick" — not "improve second serve"). One video = one plan cycle; don't
  prescribe a year.
- Pro comparisons follow references/styles.md rules: pattern resemblance, never
  level flattery.
