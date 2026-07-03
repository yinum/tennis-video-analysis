# tennis-video-analysis — Design (2026-07-02, approved)

## Goal
Given a tennis video (uploaded path or found in a folder), produce a full player skill
report: current stage (NTRP band + UTR estimate), per-dimension scores with evidence,
strengths & weaknesses, play style & specialties, pro-archetype comparison, the player's
own progress across previously analyzed videos, and a prioritized development plan.
Output: Markdown report + self-contained HTML report.

## User decisions (2026-07-02)
- Pipeline depth: full CV pipeline; must be usable by Codex as well as Claude Code.
- Historical comparison: BOTH pro-archetype mapping and own-history progress tracking.
- Rating anchor: NTRP band + rough UTR range.
- Deliverable: Markdown + self-contained HTML.
- Learn from github.com/abdullahtarek/tennis_analysis and github.com/yastrebksv/TennisProject
  (approved as the Tier-2 deep-CV backend, vendored).

## Architecture: tiered pipeline with graceful degradation
- **Tier 0 — frames + agent vision (always works).** ffmpeg/OpenCV sampling, motion-burst
  detection, contact-sheet montages. The agent reads sheets/frames against biomechanics
  references.
- **Tier 1 — pose biomechanics (most footage, any angle).** MediaPipe Pose 33 landmarks →
  joint angles, knee bend, contact-height proxy, stance ratio, hip oscillation
  (split-step proxy); annotated skeleton frames as report evidence.
- **Tier 2 — deep match analytics (broadcast-style footage only).** Court keypoint model
  (yastrebksv/TennisCourtDetector, 14 kps @640x360) → homography; YOLOv8 person detection →
  court-projected position heatmap, distance covered, movement speeds. Optional
  experimental ball/bounce pass via vendored TennisProject (TrackNet + CatBoost bounce).
  Requires elevated behind-baseline camera with full court visible; the skill triages
  footage from the first contact sheet and skips Tier 2 gracefully when unsuitable.

## Separation of skill vs data
- Skill dir (`~/.agents/skills/tennis-video-analysis/`, git-tracked, lightweight):
  SKILL.md, scripts/, references/, assets/, docs/, evals/.
- Data home (`~/.tennis-analysis/`, created by setup.sh): venv/, vendor/ (cloned repos),
  models/ (downloaded weights), players/<slug>/history.json (own-history comparison).
- Per-video work dir: `<video_dir>/<stem>_analysis/` (frames, sheets, pose, match,
  assessment.json, report.md, report.html).

## Pretrained weights (Google Drive; manual fallback documented in setup.sh)
| Model | Source repo | Drive file ID |
|---|---|---|
| Ball detector (fine-tuned YOLOv5) | abdullahtarek/tennis_analysis | 1UZwiG1jkWgce9lNhxJ2L0NVjX1vGM05U |
| Court kps CNN (ResNet-style) | abdullahtarek/tennis_analysis | 1QrTOF1ToQ4plsSZbkBs3zOLkVt3MBlta |
| Court detector 14kp @640x360 | yastrebksv/TennisCourtDetector | 1f-Co64ehgq4uddcQm1aFBDtbnyZhQvgG |
| TrackNet ball tracker | yastrebksv/TrackNet | 1XEYZ4myUN7QT-NeBYJI0xteLsvs-ZAOl |
| Bounce detector (CatBoost) | yastrebksv/TennisProject | 1Eo5HDnAQE8y_FbOftKZ8pjiojwuy2BmJ |

## Report content contract
Stage (NTRP band + UTR est., justified) · 10-dimension rubric scores with per-claim
evidence (frame refs / metrics) · strengths & weaknesses · style archetype + pro
comparisons + specialties · own-history trend (when ≥2 sessions) · prioritized
development plan with drills & success metrics · honesty section (what the footage
could not show).

Ten dimensions: Serve, Return, Forehand, Backhand, Net Game, Movement & Footwork,
Rally Consistency, Power & Spin, Tactics & Shot Selection, Competitive Habits.

## Division of labor: scripts vs agent
Scripts do everything deterministic (sampling, pose math, homography, heatmaps, HTML/MD
rendering, history persistence). The agent does perception and judgment (footage triage,
stroke reading, scoring, prose), then writes `assessment.json`; `build_report.py` turns
it into the deliverables. Report prose follows references/report-guide.md, distilled from
wshobson/agents@data-storytelling and coreyhaines31/marketingskills@copywriting.

## Codex compatibility
All scripts are plain CLI Python/bash run from the data-home venv; SKILL.md is
harness-neutral (vision steps say "view the image file"); installed via symlinks from
both agents' skill stores into `~/.agents/skills/` per the shared-store convention.
