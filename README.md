# tennis-video-analysis

An [agent skill](https://skills.sh) that turns tennis footage into an evidence-based
player skill report: NTRP band + rough UTR estimate, 10 scored skill dimensions with
frame citations, strengths/weaknesses, play-style archetype with pro pattern
comparisons, progress tracking across sessions, and a prioritized development plan —
delivered as Markdown plus a self-contained HTML report (radar chart, evidence
gallery, trend line).

Works with Claude Code, Codex, and any agent harness that can run CLI scripts and
view images.

## How it works — tiered CV pipeline with graceful degradation

| Tier | Needs | Produces |
|---|---|---|
| 0 — frames + agent vision | ffmpeg, OpenCV | motion-burst detection, timestamped contact sheets the agent reads against biomechanics references |
| 1 — pose biomechanics | MediaPipe (Tasks API) | joint angles, knee bend, stance width, rotation and split-step proxies + skeleton-annotated evidence frames |
| 2 — deep match analytics | PyTorch, ultralytics + pretrained weights | court keypoints → homography, player tracking → court-coverage heatmaps, movement speed/distance; optional ball/bounce pass |

Tier 2 requires broadcast-style footage (elevated camera behind the baseline, full
court visible) and declines gracefully otherwise — a report always ships.

## Install

```bash
git clone https://github.com/yinum/tennis-video-analysis ~/.agents/skills/tennis-video-analysis
ln -s ~/.agents/skills/tennis-video-analysis ~/.claude/skills/tennis-video-analysis   # Claude Code
ln -s ~/.agents/skills/tennis-video-analysis ~/.codex/skills/tennis-video-analysis    # Codex

bash ~/.agents/skills/tennis-video-analysis/scripts/setup.sh basic  # Tiers 0-1
bash ~/.agents/skills/tennis-video-analysis/scripts/setup.sh full   # + Tier 2 (~2 GB)
```

Heavy artifacts (venv, vendored repos, model weights, player history) live in
`~/.tennis-analysis/`, never in the skill directory.

Then ask your agent: *"analyze my tennis video at ~/Videos/match.mp4, player Alex"*.

## Companion skill

[tennis-training-plan](https://github.com/yinum/tennis-training-plan) turns a report
from this skill into a realistic periodized training plan, and prescribes the
re-assessment loop back into this one.

## Credits

Tier 2 is adapted from and vendors these excellent open-source projects at setup time:

- [abdullahtarek/tennis_analysis](https://github.com/abdullahtarek/tennis_analysis) — YOLO player/ball detection, court keypoint CNN, speed stats
- [yastrebksv/TennisProject](https://github.com/yastrebksv/TennisProject) — TrackNet ball tracking, bounce detection, homography pipeline
- [yastrebksv/TennisCourtDetector](https://github.com/yastrebksv/TennisCourtDetector) — 14-keypoint court detection model

Report-writing principles distilled from
[wshobson/agents](https://github.com/wshobson/agents) `data-storytelling` and
[coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) `copywriting`.
