# Scoring rubric: 10 dimensions → NTRP band + UTR estimate

Score each dimension 1–10 from what the video actually shows. Anchor on the
descriptions below, cite frame evidence for every score, and prefer a defensible
band over a flattering point estimate. When a dimension is barely visible in the
footage (e.g., two serves in the whole clip), score it with an explicit
low-confidence note in `evidence` rather than guessing silently.

## Score anchors (apply per dimension)

- **1–2 · Novice.** Learning contact. Rallies rarely exceed 2 balls; swing is armsy,
  no unit turn, frequent whiffs or frame hits.
- **3–4 · Developing.** Can sustain slow cooperative rallies. Recognizable swing
  shape but breaks down under pace or on the move; contact point inconsistent;
  footwork reactive, no split step.
- **5–6 · Solid intermediate.** Reliable rally ball with directional intent; basic
  spin; split step appears; can construct simple points. Technique holds until
  pressed for time or pulled wide. Most committed club players live here.
- **7–8 · Advanced.** Weapons exist; pace + spin on demand; footwork proactive
  (recovery steps, adjusting steps around the contact); tactical patterns
  (serve +1, backhand-to-backhand exchanges) executed deliberately.
- **9–10 · Elite/collegiate+.** Technically clean under full pace and stretch; shot
  tolerance high; reads the opponent early. Reserve 10 for footage indistinguishable
  from professional level. Video-only analysis should almost never award 9+.

## The 10 dimensions and what to look for

| Dimension | Key observables |
|---|---|
| Serve | stance, rhythm, toss consistency, trophy position, leg drive, contact extension, pronation, second-serve spin vs. push, landing balance |
| Return | ready position, split timing, compact swing vs. full cut, depth, direction choice vs. serve strength |
| Forehand | grip family, unit turn, spacing, contact in front, extension, finish variety, topspin control, weapon potential |
| Backhand | one/two-handed, shoulder turn, contact height comfort, slice availability, breakdown pattern under pressure |
| Net Game | approach trigger, first volley height/depth, volley technique (punch vs. swing), overhead reliability, court closing |
| Movement & Footwork | split step presence/timing, first-step burst, adjusting steps, recovery to neutral, defensive slide/stretch, balance at contact |
| Rally Consistency | unforced-error tempo, shot tolerance (balls per rally before error), margin over net, depth discipline |
| Power & Spin | racquet-head speed, comfort adding pace, spin as intent vs. accident, flatten-out ability |
| Tactics & Shot Selection | patterns (serve +1, attack short balls), direction changes at right times, risk calibration, opponent exploitation |
| Competitive Habits | between-point routines, body language after errors, decision quality when tight, energy across the session |

## Mapping scores → NTRP

Compute the profile average, then weight reality: **Rally Consistency, Movement, and
Serve carry NTRP more than the rest** — a huge forehand with 3-ball tolerance is not
a 4.5. Sanity-check the band against these gate descriptions:

| NTRP | Gate description (must be true of the video) |
|---|---|
| 1.5–2.0 | learning strokes; cannot sustain a rally |
| 2.5 | sustains slow short rallies; big technical gaps |
| 3.0 | consistent on medium-pace balls hit right at them; weak vs. depth/pace/spin |
| 3.5 | directional control appears; still shaky on the move; developing net game |
| 4.0 | dependable strokes both wings, uses spin/lobs/volleys, rally tolerance solid |
| 4.5 | pace and spin used deliberately; footwork controls points; first-serve weapon |
| 5.0 | shot anticipation, can structure around a weapon; punishes short balls reliably |
| 5.5–6.0 | tournament-hardened; sustained power + consistency; near-collegiate |
| 6.5–7.0 | world-class; not assessable from amateur footage — do not assign |

Rough profile-average → NTRP starting point (then apply gates):
avg 2 → ~2.0 · avg 3 → ~2.5–3.0 · avg 4 → ~3.0–3.5 · avg 5 → ~3.5–4.0 ·
avg 6 → ~4.0–4.5 · avg 7 → ~4.5–5.0 · avg 8 → ~5.0+.

**Always report a half-point band** (e.g., "3.5, band 3.0–4.0"): one video cannot
resolve finer than that, and inflated single numbers destroy trust.

## UTR estimate

UTR is match-result-based; from video you can only offer a coarse range. Use:
NTRP 2.5 ≈ UTR 1–2 · 3.0 ≈ 2–3 · 3.5 ≈ 3–4 · 4.0 ≈ 4–6 · 4.5 ≈ 6–8 ·
5.0 ≈ 8–10 · 5.5 ≈ 10–12. Label it "rough, video-based" in the report.

## Calibration rules

- Score what you SEE, not what the stroke could become. Potential goes in the
  development plan, not the score.
- Cooperative rallying inflates apparent level by ~0.5 NTRP versus match play;
  note the session type and discount accordingly.
- If the opponent is much weaker/stronger, consistency numbers are distorted —
  say so in caveats.
- Practice-swing beauty ≠ level. Weight contact quality, balance at contact, and
  error tempo over aesthetics.
- Use `pose/pose_metrics.json` and `match/match_metrics.json` numbers as evidence
  where available (knee bend on serve, distance covered, net-approach fraction) —
  cite them in the dimension's `evidence` field.
