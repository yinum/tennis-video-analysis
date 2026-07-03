---
name: tennis-video-analysis
description: >-
  Analyze a tennis video (uploaded file or one found in a folder) and generate a full
  player skill report: current stage (NTRP band + rough UTR), 10-dimension skill scores
  with frame evidence, strengths and weaknesses, play style and specialties, pro-archetype
  comparison, progress vs. the player's previous analyzed sessions, and a prioritized
  development plan — delivered as Markdown plus a self-contained HTML report. Uses a
  tiered CV pipeline (frame sampling + agent vision; MediaPipe pose biomechanics; court
  homography + player tracking adapted from abdullahtarek/tennis_analysis and
  yastrebksv/TennisProject). Use this skill whenever the user mentions analyzing tennis
  footage, a tennis match/practice video, "how good is this player", tennis skill
  assessment, player report, NTRP/UTR estimation from video, tennis technique review,
  or points at a folder containing tennis videos — even if they don't say "analyze".
---

# Tennis Video Analysis

Turn tennis footage into an evidence-based player skill report. The pipeline is
tiered so a report always ships: perception scripts do the deterministic work, you
do the seeing and judging, and `build_report.py` renders the deliverables.

**Paths used throughout** (all harnesses — plain CLI):
- `SKILL_DIR` = this skill's directory; scripts in `SKILL_DIR/scripts/`
- `TENNIS_HOME` = `~/.tennis-analysis` (override via `$TENNIS_ANALYSIS_HOME`): venv,
  vendored repos, model weights, player history
- `VENV_PY` = `$TENNIS_HOME/venv/bin/python`
- `ADIR` = `<video_dir>/<video_stem>_analysis/` — all per-video outputs

## Workflow

### 0. Check setup (once per machine)

Run `bash SKILL_DIR/scripts/setup.sh status`. If Tier 0–1 pieces are missing, run
`setup.sh basic` (ffmpeg + venv + OpenCV/MediaPipe — a few minutes). Tier 2 needs
`setup.sh full` (~2 GB of torch/ultralytics plus five pretrained weights from
Google Drive) — ask the user before triggering that download the first time; if
weight downloads fail, the script prints manual-download URLs. Never block the
report on Tier 2: everything degrades gracefully.

### 1. Locate the video and identify the player

- Given a path, use it. Given a folder, list `*.mp4 *.mov *.avi *.mkv *.MP4 *.MOV`
  and confirm with the user if several match.
- Ask (or infer from the request) the player's name and which player in the frame
  is the subject — default: the near-side (bottom) player. The name keys the
  history file, so keep it consistent across sessions ("Yi", not "yi_video2").

### 2. Extract frames and find the action

```bash
$VENV_PY SKILL_DIR/scripts/extract_frames.py VIDEO
```
Produces `ADIR/` with overview contact sheets, per-burst dense sheets (high-motion
segments ≈ strokes/rallies), and `segments.json`.

### 3. Triage the footage (vision pass 1)

View `ADIR/sheets/overview_*.jpg`. Decide and note:
- Camera angle: elevated behind-baseline with full court visible → Tier 2 eligible;
  side/net-level/partial court → Tiers 0–1 only.
- Session type: match / rally practice / drills / serve basket (changes rubric
  calibration — see references/rubric.md).
- Which bursts show which strokes; whether the subject player is trackable.

### 4. Run the metric tiers (parallel where possible)

```bash
$VENV_PY SKILL_DIR/scripts/pose_metrics.py ADIR                    # Tier 1, any footage
$VENV_PY SKILL_DIR/scripts/match_analytics.py VIDEO ADIR           # Tier 2, broadcast-style only
```
Tier 2 accepts `--with-ball` for the experimental TennisProject ball/bounce video
(slow; only when the user wants shot-placement evidence). Both scripts write
`{"available": false, "reason": ...}` instead of failing — read their JSON outputs
and carry on with whatever is available.

### 5. Deep vision pass (the heart of the analysis)

Read `references/biomechanics.md`, then view, in order:
1. every `ADIR/sheets/burst_*.jpg` (stroke mechanics at 8 fps),
2. `ADIR/pose/annotated/*.jpg` (skeleton overlays; corroborate against
   `pose/pose_metrics.json` numbers),
3. `ADIR/match/heatmap_*.png` and `match/match_metrics.json` if available,
4. individual frames from `ADIR/frames/burst_*/` when a sheet tile needs a closer look.

Collect evidence per rubric dimension as you go — frame filenames, timestamps,
metric values. Look for what repeats across bursts; one bad swing is noise, the
same flaw in four bursts is a finding.

### 6. Score, classify, compare

- Score the 10 dimensions with `references/rubric.md`; derive NTRP band + UTR range.
- Classify style + pick 1–3 pro comparisons with `references/styles.md`.
- Check history: `TENNIS_HOME/players/<slug>/history.json` (slug = lowercase
  hyphenated name). If previous sessions exist, compare dimension-by-dimension and
  write the progress narrative (what improved, what regressed, was the last plan
  followed).

### 7. Write the assessment

Read `references/report-guide.md` first (voice, evidence discipline, narrative
spine). Then write `ADIR/assessment.json`:

```json
{
  "player": "Yi", "date": "2026-07-03", "session_type": "rally practice",
  "video": "/path/video.mp4",
  "footage_quality": {"tiers_run": [0, 1, 2], "camera": "elevated behind baseline",
                      "limitations": ["no full match play", "8 serves visible"]},
  "stage": {"ntrp": 3.5, "ntrp_band": "3.0-4.0", "utr_range": "3-4",
            "justification": "markdown-capable prose ..."},
  "dimensions": [
    {"name": "Serve", "score": 4.0, "evidence": "burst 2+5: no leg drive (knee 168deg), trophy elbow low", "notes": "..."}
    // exactly these 10 names: Serve, Return, Forehand, Backhand, Net Game,
    // Movement & Footwork, Rally Consistency, Power & Spin,
    // Tactics & Shot Selection, Competitive Habits
  ],
  "strengths":  [{"title": "finding-style headline", "detail": "...", "evidence": "frames/burst_3/..."}],
  "weaknesses": [{"title": "...", "detail": "...", "evidence": "...", "fix": "one-line prescription"}],
  "style": {"archetype": "Counterpuncher", "description": "markdown prose",
            "pro_comparisons": [{"player": "Medvedev", "why": "pattern resemblance, never level"}],
            "specialties": ["deep cross-court backhand", "lob defense"]},
  "tactics": "markdown prose on patterns, court position, shot selection",
  "history_comparison": "markdown prose (omit on first session)",
  "development_plan": [{"priority": 1, "focus": "...", "drills": ["...", "..."],
                        "success_metric": "measurable, e.g. 8/10 second serves with visible kick"}],
  "caveats": ["single session", "no doubles/match context", "..."],
  "key_frames": ["pose/annotated/...jpg", "frames/burst_2/...jpg"]
}
```

### 8. Build and deliver

```bash
python3 SKILL_DIR/scripts/build_report.py ADIR --player "Yi"
```
Writes `ADIR/report.md` + self-contained `ADIR/report.html` (radar, dimension
table, evidence gallery, progress trend once ≥2 sessions) and appends the session
to the player's history. Then: summarize the top-line findings in chat (stage,
one headline strength, the #1 fix), give both file paths, and — if the harness can
render HTML artifacts — offer to display the HTML report.

## Honesty requirements (non-negotiable)

- Every score and claim cites visible evidence; low-coverage dimensions say so.
- Report bands, not flattering points; video-only NTRP is an estimate, label it so.
- `caveats` is a real section: what the footage cannot show (match temperament,
  stamina, the other 80% of the serve count...).
- Pro comparisons are pattern resemblance, never "you play like X".

## Troubleshooting

| Symptom | Action |
|---|---|
| mediapipe/opencv import errors | re-run `setup.sh basic`; if mediapipe wheels fail on this Python, report Tier 1 unavailable and proceed Tier 0 |
| Tier 2 "court not detected reliably" | expected on non-broadcast footage — proceed without it, mention in caveats |
| gdown quota errors on weights | give the user the manual Drive URLs printed by setup.sh; Tier 2 waits |
| Video won't decode | `ffmpeg -i in -c:v libx264 -crf 20 out.mp4` and retry |
| Two players on the near side (doubles) | note it; MediaPipe tracks the most prominent person — crop with ffmpeg `crop` filter to isolate the subject if needed |
| `assessment.json` rejected | build_report.py names the missing keys; fix and re-run |

## Codex / non-Claude harnesses

Everything above is plain bash + python CLI; "view" steps mean opening the image
files with whatever vision the harness has. No Claude-specific tools are required.
