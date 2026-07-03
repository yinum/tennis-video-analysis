#!/usr/bin/env python
"""Tier 1: biomechanics metrics from MediaPipe Pose (Tasks API) over the high-motion
bursts found by extract_frames.py. Produces numeric proxies (joint angles, stance,
rotation, contact-height) plus skeleton-annotated frames for the report.

Run with the venv python AFTER extract_frames.py:
  ~/.tennis-analysis/venv/bin/python pose_metrics.py ANALYSIS_DIR

Outputs into ANALYSIS_DIR/pose/:
  pose_metrics.json     per-burst aggregates + per-frame records
  annotated/*.jpg       skeleton overlays on the most informative frames

Honesty notes: these are 2D image-plane proxies, not lab biomechanics. The
landmarker tracks the most prominent person — on behind-court footage that is the
near-side player. Interpretation guidance lives in references/biomechanics.md.
"""
import argparse, json, math, os, sys
from pathlib import Path

import cv2
import numpy as np

TENNIS_HOME = Path(os.environ.get("TENNIS_ANALYSIS_HOME", Path.home() / ".tennis-analysis"))
POSE_MODEL = TENNIS_HOME / "models" / "pose_landmarker_lite.task"

# 33-landmark topology indices (MediaPipe pose)
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

CONNECTIONS = [(L_SHOULDER, R_SHOULDER), (L_HIP, R_HIP),
               (L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST),
               (R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST),
               (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP),
               (L_HIP, L_KNEE), (L_KNEE, L_ANKLE),
               (R_HIP, R_KNEE), (R_KNEE, R_ANKLE)]


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


def draw_skeleton(img, lm, w, h):
    im2 = img.copy()
    pts = [(int(p.x * w), int(p.y * h)) for p in lm]
    for a, b in CONNECTIONS:
        cv2.line(im2, pts[a], pts[b], (80, 220, 120), 2, cv2.LINE_AA)
    for i in (NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST,
              L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE):
        cv2.circle(im2, pts[i], 4, (40, 120, 255), -1, cv2.LINE_AA)
    return im2


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
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except Exception as e:
        fail(outdir, f"mediapipe unavailable: {e}")
    if not POSE_MODEL.exists():
        fail(outdir, f"pose model missing at {POSE_MODEL} — run setup.sh basic")

    seg_file = adir / "segments.json"
    if not seg_file.exists():
        fail(outdir, "segments.json not found — run extract_frames.py first")
    segments = json.loads(seg_file.read_text())

    ann_dir.mkdir(parents=True, exist_ok=True)
    landmarker = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(POSE_MODEL)),
        running_mode=vision.RunningMode.IMAGE, num_poses=1))

    bursts_out = []
    for b in segments.get("bursts", []):
        bdir = adir / b.get("frames_dir", "")
        frame_files = sorted(bdir.glob("*.jpg")) if bdir.is_dir() else []
        records, cache = [], {}
        for f in frame_files:
            img = cv2.imread(str(f))
            if img is None:
                continue
            h, w = img.shape[:2]
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                              data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            try:
                res = landmarker.detect(mp_img)
            except Exception:
                continue
            if not res.pose_landmarks:
                continue
            lm = res.pose_landmarks[0]
            vis_vals = [getattr(p, "visibility", 1.0) or 1.0 for p in lm]
            vis = float(np.mean(vis_vals))
            if vis < args.min_visibility:
                continue

            def pt(i):
                return (lm[i].x * w, lm[i].y * h)

            sh_l, sh_r = pt(L_SHOULDER), pt(R_SHOULDER)
            hp_l, hp_r = pt(L_HIP), pt(R_HIP)
            sh_c = ((sh_l[0] + sh_r[0]) / 2, (sh_l[1] + sh_r[1]) / 2)
            hp_c = ((hp_l[0] + hp_r[0]) / 2, (hp_l[1] + hp_r[1]) / 2)
            sh_w = abs(sh_l[0] - sh_r[0]) or 1.0
            wr_l, wr_r = pt(L_WRIST), pt(R_WRIST)

            rec = {
                "file": f"{b.get('frames_dir')}/{f.name}",
                "t": float(f.stem.split("_")[-1].rstrip("s")),
                "visibility": round(vis, 2),
                "knee_angle_l": angle(pt(L_HIP), pt(L_KNEE), pt(L_ANKLE)),
                "knee_angle_r": angle(pt(R_HIP), pt(R_KNEE), pt(R_ANKLE)),
                "elbow_angle_l": angle(sh_l, pt(L_ELBOW), wr_l),
                "elbow_angle_r": angle(sh_r, pt(R_ELBOW), wr_r),
                "stance_width_ratio": round(abs(pt(L_ANKLE)[0] - pt(R_ANKLE)[0]) / sh_w, 2),
                "shoulder_hip_sep_deg": round(abs(line_angle_deg(sh_l, sh_r) - line_angle_deg(hp_l, hp_r)), 1),
                "trunk_lean_deg": round(abs(90 - abs(line_angle_deg(hp_c, sh_c))), 1),
                "wrist_above_head": bool(min(lm[L_WRIST].y, lm[R_WRIST].y) < lm[NOSE].y),
                "hip_center_y_norm": round(hp_c[1] / h, 3),
                "wrist_l_xy": [round(wr_l[0]), round(wr_l[1])],
                "wrist_r_xy": [round(wr_r[0]), round(wr_r[1])],
            }
            records.append(rec)
            cache[rec["file"]] = (img, lm, w, h)

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
            oh_frac = float(np.mean([r["wrist_above_head"] for r in records]))
            summary = {
                "n_tracked_frames": len(records),
                "deepest_knee_angle": knee_min,
                "max_shoulder_hip_sep_deg": max(seps) if seps else None,
                "mean_stance_width_ratio": round(float(np.mean([r["stance_width_ratio"] for r in records])), 2),
                "wrist_above_head_frac": round(oh_frac, 2),
                "hip_vertical_oscillation": round(float(np.std(hips)), 3),
                "likely_overhead_action": oh_frac > 0.15,
                "faster_wrist": "left" if speed_l > speed_r * 1.15 else ("right" if speed_r > speed_l * 1.15 else "unclear"),
            }
            # Annotate the most informative frames: deepest knee bend, max rotation, overhead
            picks = set()
            with_knee = [r for r in records if r["knee_angle_r"] is not None]
            if with_knee:
                picks.add(min(with_knee, key=lambda r: r["knee_angle_r"])["file"])
            if seps:
                picks.add(max((r for r in records if r["shoulder_hip_sep_deg"] is not None),
                              key=lambda r: r["shoulder_hip_sep_deg"])["file"])
            oh = [r for r in records if r["wrist_above_head"]]
            if oh:
                picks.add(oh[len(oh) // 2]["file"])
            annotated = []
            for pf in picks:
                img, lm, w, h = cache[pf]
                name = f"burst{b['index']}_" + Path(pf).name
                cv2.imwrite(str(ann_dir / name), draw_skeleton(img, lm, w, h),
                            [cv2.IMWRITE_JPEG_QUALITY, 88])
                annotated.append(f"pose/annotated/{name}")
            summary["annotated_frames"] = annotated

        bursts_out.append({"burst": b["index"], "start_s": b["start_s"], "end_s": b["end_s"],
                           "summary": summary, "frames": records})

    tracked = [b for b in bursts_out if b["summary"]]
    hand_votes = [b["summary"]["faster_wrist"] for b in tracked]
    result = {
        "available": True,
        "n_bursts_tracked": len(tracked),
        "handedness_guess": (max(set(hand_votes), key=hand_votes.count) if hand_votes else "unknown"),
        "bursts": bursts_out,
    }
    (outdir / "pose_metrics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"available": True, "n_bursts_tracked": len(tracked),
                      "handedness_guess": result["handedness_guess"],
                      "annotated": [f for b in tracked for f in b["summary"].get("annotated_frames", [])]},
                     indent=2))


if __name__ == "__main__":
    main()
