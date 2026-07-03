#!/usr/bin/env python
"""Tier 1: biomechanics metrics from MediaPipe Pose over the high-motion bursts found
by extract_frames.py. Produces numeric proxies (joint angles, stance, rotation,
contact-height) plus skeleton-annotated frames for the report.

Run with the venv python AFTER extract_frames.py:
  ~/.tennis-analysis/venv/bin/python pose_metrics.py ANALYSIS_DIR

Outputs into ANALYSIS_DIR/pose/:
  pose_metrics.json     per-burst aggregates + per-frame records
  annotated/*.jpg       skeleton overlays on the most informative frames

Notes on honesty: these are 2D image-plane proxies, not lab biomechanics. MediaPipe
tracks the most prominent person — on behind-court footage that is the near-side
player. All interpretation guidance lives in references/biomechanics.md.
"""
import argparse, json, math, sys
from pathlib import Path

import cv2
import numpy as np


def fail(outdir, reason):
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "pose_metrics.json").write_text(json.dumps(
        {"available": False, "reason": reason}, indent=2))
    print(json.dumps({"available": False, "reason": reason}))
    sys.exit(0)


def angle(a, b, c):
    """Angle ABC in degrees from 2D points."""
    ba, bc = np.array(a) - np.array(b), np.array(c) - np.array(b)
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-9:
        return None
    cosv = float(np.clip(np.dot(ba, bc) / denom, -1, 1))
    return round(math.degrees(math.acos(cosv)), 1)


def line_angle_deg(p1, p2):
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_dir")
    ap.add_argument("--min-visibility", type=float, default=0.5)
    args = ap.parse_args()

    adir = Path(args.analysis_dir).expanduser().resolve()
    outdir = adir / "pose"
    ann_dir = outdir / "annotated"

    try:
        import mediapipe as mp
    except Exception as e:  # keep the pipeline alive on any import failure
        fail(outdir, f"mediapipe unavailable: {e}")

    seg_file = adir / "segments.json"
    if not seg_file.exists():
        fail(outdir, "segments.json not found — run extract_frames.py first")
    segments = json.loads(seg_file.read_text())

    ann_dir.mkdir(parents=True, exist_ok=True)
    mp_pose = mp.solutions.pose
    drawer = mp.solutions.drawing_utils

    L = mp_pose.PoseLandmark
    bursts_out = []

    with mp_pose.Pose(model_complexity=1, static_image_mode=False) as pose:
        for b in segments.get("bursts", []):
            bdir = adir / b.get("frames_dir", "")
            frame_files = sorted(bdir.glob("*.jpg")) if bdir.is_dir() else []
            records, cache = [], {}
            for f in frame_files:
                img = cv2.imread(str(f))
                if img is None:
                    continue
                h, w = img.shape[:2]
                res = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                if not res.pose_landmarks:
                    continue
                lm = res.pose_landmarks.landmark
                vis = float(np.mean([p.visibility for p in lm]))
                if vis < args.min_visibility:
                    continue

                def pt(i):
                    return (lm[i].x * w, lm[i].y * h)

                sh_l, sh_r = pt(L.LEFT_SHOULDER), pt(L.RIGHT_SHOULDER)
                hp_l, hp_r = pt(L.LEFT_HIP), pt(L.RIGHT_HIP)
                sh_c = ((sh_l[0] + sh_r[0]) / 2, (sh_l[1] + sh_r[1]) / 2)
                hp_c = ((hp_l[0] + hp_r[0]) / 2, (hp_l[1] + hp_r[1]) / 2)
                sh_w = abs(sh_l[0] - sh_r[0]) or 1.0
                wr_l, wr_r = pt(L.LEFT_WRIST), pt(L.RIGHT_WRIST)
                nose_y = lm[L.NOSE].y

                rec = {
                    "file": f"{b.get('frames_dir')}/{f.name}",
                    "t": float(f.stem.split("_")[-1].rstrip("s")),
                    "visibility": round(vis, 2),
                    "knee_angle_l": angle(pt(L.LEFT_HIP), pt(L.LEFT_KNEE), pt(L.LEFT_ANKLE)),
                    "knee_angle_r": angle(pt(L.RIGHT_HIP), pt(L.RIGHT_KNEE), pt(L.RIGHT_ANKLE)),
                    "elbow_angle_l": angle(sh_l, pt(L.LEFT_ELBOW), wr_l),
                    "elbow_angle_r": angle(sh_r, pt(L.RIGHT_ELBOW), wr_r),
                    "stance_width_ratio": round(abs(pt(L.LEFT_ANKLE)[0] - pt(L.RIGHT_ANKLE)[0]) / sh_w, 2),
                    "shoulder_hip_sep_deg": round(abs(line_angle_deg(sh_l, sh_r) - line_angle_deg(hp_l, hp_r)), 1),
                    "trunk_lean_deg": round(abs(90 - abs(line_angle_deg(hp_c, sh_c))), 1),
                    "wrist_above_head": bool(min(lm[L.LEFT_WRIST].y, lm[L.RIGHT_WRIST].y) < nose_y),
                    "hip_center_y_norm": round(hp_c[1] / h, 3),
                    "wrist_l_xy": [round(wr_l[0]), round(wr_l[1])],
                    "wrist_r_xy": [round(wr_r[0]), round(wr_r[1])],
                }
                records.append(rec)
                cache[rec["file"]] = (img, res)

            summary = None
            if records:
                knee_min = min((r[k] for r in records for k in ("knee_angle_l", "knee_angle_r")
                                if r[k] is not None), default=None)
                seps = [r["shoulder_hip_sep_deg"] for r in records if r["shoulder_hip_sep_deg"] is not None]
                hips = [r["hip_center_y_norm"] for r in records]
                wl = np.array([r["wrist_l_xy"] for r in records], float)
                wr = np.array([r["wrist_r_xy"] for r in records], float)
                speed_l = float(np.mean(np.linalg.norm(np.diff(wl, axis=0), axis=1))) if len(wl) > 1 else 0
                speed_r = float(np.mean(np.linalg.norm(np.diff(wr, axis=0), axis=1))) if len(wr) > 1 else 0
                summary = {
                    "n_tracked_frames": len(records),
                    "deepest_knee_angle": knee_min,
                    "max_shoulder_hip_sep_deg": max(seps) if seps else None,
                    "mean_stance_width_ratio": round(float(np.mean([r["stance_width_ratio"] for r in records])), 2),
                    "wrist_above_head_frac": round(float(np.mean([r["wrist_above_head"] for r in records])), 2),
                    "hip_vertical_oscillation": round(float(np.std(hips)), 3),
                    "likely_overhead_action": float(np.mean([r["wrist_above_head"] for r in records])) > 0.15,
                    "faster_wrist": "left" if speed_l > speed_r * 1.15 else ("right" if speed_r > speed_l * 1.15 else "unclear"),
                }
                # Annotate the most informative frames: deepest knee bend, max rotation, overhead
                picks = set()
                def pick(key, cond=lambda r: True, reverse=False):
                    cands = [r for r in records if cond(r) and r.get(key) is not None]
                    if cands:
                        picks.add(sorted(cands, key=lambda r: r[key], reverse=reverse)[0]["file"])
                pick("knee_angle_r")
                pick("shoulder_hip_sep_deg", reverse=True)
                oh = [r for r in records if r["wrist_above_head"]]
                if oh:
                    picks.add(oh[len(oh) // 2]["file"])
                annotated = []
                for pf in picks:
                    img, res = cache[pf]
                    im2 = img.copy()
                    drawer.draw_landmarks(im2, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                    name = f"burst{b['index']}_" + Path(pf).name
                    cv2.imwrite(str(ann_dir / name), im2, [cv2.IMWRITE_JPEG_QUALITY, 88])
                    annotated.append(f"pose/annotated/{name}")
                summary["annotated_frames"] = annotated

            bursts_out.append({"burst": b["index"], "start_s": b["start_s"], "end_s": b["end_s"],
                               "summary": summary, "frames": records})

    tracked = [b for b in bursts_out if b["summary"]]
    result = {
        "available": True,
        "n_bursts_tracked": len(tracked),
        "handedness_guess": (max((b["summary"]["faster_wrist"] for b in tracked),
                                 key=lambda v: sum(1 for b in tracked if b["summary"]["faster_wrist"] == v))
                             if tracked else "unknown"),
        "bursts": bursts_out,
    }
    (outdir / "pose_metrics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"available": True, "n_bursts_tracked": len(tracked),
                      "annotated": [f for b in tracked for f in b["summary"].get("annotated_frames", [])]},
                     indent=2))


if __name__ == "__main__":
    main()
