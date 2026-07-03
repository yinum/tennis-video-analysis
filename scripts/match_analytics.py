#!/usr/bin/env python
"""Tier 2: deep match analytics for broadcast-style footage (elevated camera behind the
baseline, full court visible). Adapted from yastrebksv/TennisCourtDetector (court
keypoints -> homography) plus ultralytics YOLOv8 person detection. Produces court-
projected position heatmaps and movement statistics per player; optionally runs the
full vendored TennisProject pipeline (TrackNet ball + bounce map) as an annotated video.

Run with the venv python AFTER extract_frames.py:
  ~/.tennis-analysis/venv/bin/python match_analytics.py VIDEO ANALYSIS_DIR [--with-ball]

Outputs into ANALYSIS_DIR/match/:
  match_metrics.json    availability, court confidence, per-player movement stats
  heatmap_near.png / heatmap_far.png   court-coverage heatmaps
  ball_annotated.mp4    (only with --with-ball; experimental)

Degrades gracefully: any missing dependency/weights, or an undetectable court, writes
{"available": false, "reason": ...} and exits 0 so Tiers 0-1 still carry the report.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

import numpy as np

TENNIS_HOME = Path(os.environ.get("TENNIS_ANALYSIS_HOME", Path.home() / ".tennis-analysis"))
MODELS = TENNIS_HOME / "models"
VENDOR = TENNIS_HOME / "vendor"

# 14 reference keypoints from yastrebksv/TennisCourtDetector court_reference.py.
# Reference frame: ~100 px per meter; doubles corners at indices 0-3; net at y=1748.
REF_KPS = np.array([
    (286, 561), (1379, 561), (286, 2935), (1379, 2935),      # doubles corners TL TR BL BR
    (423, 561), (423, 2935), (1242, 561), (1242, 2935),      # singles lines
    (423, 1110), (1242, 1110), (423, 2386), (1242, 2386),    # service lines top/bottom
    (832, 1110), (832, 2386),                                 # center service line
], dtype=np.float32)
COURT_W_M, COURT_L_M = 10.97, 23.77
SX = COURT_W_M / (1379 - 286)   # meters per reference px (x)
SY = COURT_L_M / (2935 - 561)   # meters per reference px (y)
ORIGIN = np.array([286.0, 561.0])  # far-left doubles corner -> court coords (0,0)
NET_Y_M = COURT_L_M / 2


def bail(outdir, reason):
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "match_metrics.json").write_text(json.dumps(
        {"available": False, "reason": reason}, indent=2))
    print(json.dumps({"available": False, "reason": reason}))
    sys.exit(0)


def to_court_m(ref_xy):
    return (np.asarray(ref_xy, float) - ORIGIN) * np.array([SX, SY])


def detect_court_kps(model, torch, frame, device):
    """Return (14x2 array in frame coords or None-rows, n_valid)."""
    import cv2
    h, w = frame.shape[:2]
    img = cv2.resize(frame, (640, 360)).astype(np.float32) / 255.0
    inp = torch.from_numpy(np.rollaxis(img, 2, 0)).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(inp.float())
    pred = torch.sigmoid(out).detach().cpu().numpy()[0]
    sys.path.insert(0, str(VENDOR / "TennisCourtDetector"))
    from postprocess import postprocess
    kps, n_valid = np.full((14, 2), np.nan), 0
    for i in range(14):
        heat = (pred[i] * 255).astype(np.uint8)
        x, y = postprocess(heat, low_thresh=170, max_radius=25)
        if x is not None and y is not None:
            kps[i] = (x * w / 640.0, y * h / 360.0)
            n_valid += 1
    return kps, n_valid


def draw_court_heatmap(points_m, out_png, title):
    """Render court diagram + visit heatmap. points_m: Nx2 court-meter coords."""
    import cv2
    ppm, mg = 28, 60  # px per meter, margin px
    W, H = int(COURT_W_M * ppm) + 2 * mg, int(COURT_L_M * ppm) + 2 * mg
    img = np.full((H, W, 3), 34, np.uint8)

    def px(xm, ym):
        return int(mg + xm * ppm), int(mg + ym * ppm)

    lines_m = [((0, 0), (COURT_W_M, 0)), ((0, COURT_L_M), (COURT_W_M, COURT_L_M)),
               ((0, 0), (0, COURT_L_M)), ((COURT_W_M, 0), (COURT_W_M, COURT_L_M)),
               ((1.37, 0), (1.37, COURT_L_M)), ((COURT_W_M - 1.37, 0), (COURT_W_M - 1.37, COURT_L_M)),
               ((1.37, 5.485), (COURT_W_M - 1.37, 5.485)),
               ((1.37, COURT_L_M - 5.485), (COURT_W_M - 1.37, COURT_L_M - 5.485)),
               ((COURT_W_M / 2, 5.485), (COURT_W_M / 2, COURT_L_M - 5.485)),
               ((0, NET_Y_M), (COURT_W_M, NET_Y_M))]
    if len(points_m):
        heat = np.zeros((H, W), np.float32)
        for xm, ym in points_m:
            x, y = px(xm, ym)
            if 0 <= x < W and 0 <= y < H:
                heat[y, x] += 1
        heat = cv2.GaussianBlur(heat, (0, 0), ppm * 0.6)
        if heat.max() > 0:
            # single-hue sequential ramp (dark->light blue), not a rainbow colormap
            anchors = np.array([(129, 66, 16), (229, 135, 57), (244, 197, 158), (251, 226, 205)], float)  # BGR
            xs = np.linspace(0, 255, len(anchors))
            lut = np.stack([np.interp(np.arange(256), xs, anchors[:, c]) for c in range(3)], 1).astype(np.uint8)
            hm = lut[(heat / heat.max() * 255).astype(np.uint8)]
            mask = (heat / heat.max() * 0.8)[..., None]
            img = (img * (1 - mask) + hm * mask).astype(np.uint8)
    for a, b in lines_m:
        cv2.line(img, px(*a), px(*b), (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(out_png), img)


def movement_stats(track, stride_s):
    """track: list of (t, x_m, y_m). Distances skip >4m/sample jumps (ID switches)."""
    if len(track) < 4:
        return None
    arr = np.array(track)
    d = np.linalg.norm(np.diff(arr[:, 1:3], axis=0), axis=1)
    ok = d < 4.0
    speeds = d[ok] / stride_s
    moving = speeds[speeds > 0.5]
    ys = arr[:, 2]
    return {
        "samples": len(track),
        "distance_m": round(float(d[ok].sum()), 1),
        "avg_moving_speed_ms": round(float(moving.mean()), 2) if len(moving) else 0.0,
        "peak_speed_ms": round(float(np.percentile(speeds, 95)), 2) if len(speeds) else 0.0,
        "deuce_side_frac": round(float(np.mean(arr[:, 1] > COURT_W_M / 2)), 2),
        "mean_dist_behind_baseline_m": None,  # filled by caller (side-dependent)
        "net_approach_frac": None,            # filled by caller
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("analysis_dir")
    ap.add_argument("--stride-s", type=float, default=0.25)
    ap.add_argument("--court-every-s", type=float, default=2.0)
    ap.add_argument("--max-minutes", type=float, default=20.0)
    ap.add_argument("--with-ball", action="store_true")
    args = ap.parse_args()

    adir = Path(args.analysis_dir).expanduser().resolve()
    outdir = adir / "match"
    video = Path(args.video).expanduser().resolve()

    try:
        import cv2, torch
        from ultralytics import YOLO
    except Exception as e:
        bail(outdir, f"Tier-2 dependencies unavailable ({e}); run setup.sh full")

    court_w = MODELS / "court_detector.pt"
    tcd = VENDOR / "TennisCourtDetector"
    if not court_w.exists() or not tcd.is_dir():
        bail(outdir, "court model or vendored TennisCourtDetector missing; run setup.sh full")

    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    sys.path.insert(0, str(tcd))
    from tracknet import BallTrackerNet
    model = BallTrackerNet(out_channels=15)
    try:
        sd = torch.load(court_w, map_location=device)
    except Exception:
        sd = torch.load(court_w, map_location=device, weights_only=False)
    model.load_state_dict(sd)
    model = model.to(device).eval()

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = min(n_frames / fps, args.max_minutes * 60)

    # Court homographies at a slow cadence (camera is mostly static)
    homos = []  # (t, H)
    valid_counts = []
    t = 0.0
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret:
            break
        kps, n_valid = detect_court_kps(model, torch, frame, device)
        valid_counts.append(n_valid)
        good = ~np.isnan(kps[:, 0])
        if n_valid >= 6:
            H, _ = cv2.findHomography(kps[good], REF_KPS[good], cv2.RANSAC, 10.0)
            if H is not None:
                homos.append((t, H))
        t += args.court_every_s

    med_valid = float(np.median(valid_counts)) if valid_counts else 0
    if not homos or med_valid < 6:
        bail(outdir, f"court not detected reliably (median {med_valid:.0f}/14 keypoints). "
                     "Tier 2 needs an elevated behind-baseline camera with the full court visible.")

    outdir.mkdir(parents=True, exist_ok=True)
    os.chdir(MODELS)  # ultralytics downloads yolov8n.pt into cwd if absent
    yolo = YOLO("yolov8n.pt")

    homo_ts = np.array([h[0] for h in homos])
    tracks = {"near": [], "far": []}
    t = 0.0
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret:
            break
        H = homos[int(np.argmin(np.abs(homo_ts - t)))][1]
        res = yolo.predict(frame, classes=[0], conf=0.4, verbose=False)[0]
        cands = {"near": [], "far": []}
        for box in res.boxes.xyxy.cpu().numpy():
            foot = np.array([[[(box[0] + box[2]) / 2, box[3]]]], np.float32)
            ref = cv2.perspectiveTransform(foot, H)[0, 0]
            xm, ym = to_court_m(ref)
            if -3 <= xm <= COURT_W_M + 3 and -6 <= ym <= COURT_L_M + 8:
                side = "near" if ym > NET_Y_M else "far"
                area = (box[2] - box[0]) * (box[3] - box[1])
                cands[side].append((area, xm, ym))
        for side in ("near", "far"):
            if cands[side]:
                if tracks[side]:
                    _, px_, py_ = tracks[side][-1]
                    best = min(cands[side], key=lambda c: (c[1] - px_) ** 2 + (c[2] - py_) ** 2)
                else:
                    best = max(cands[side], key=lambda c: c[0])
                tracks[side].append((t, best[1], best[2]))
        t += args.stride_s

    players = {}
    for side in ("near", "far"):
        st = movement_stats(tracks[side], args.stride_s)
        if st:
            arr = np.array(tracks[side])
            if side == "near":
                st["mean_dist_behind_baseline_m"] = round(float(np.mean(np.maximum(arr[:, 2] - COURT_L_M, 0))), 2)
                st["net_approach_frac"] = round(float(np.mean(arr[:, 2] < NET_Y_M + 3.5)), 2)
            else:
                st["mean_dist_behind_baseline_m"] = round(float(np.mean(np.maximum(-arr[:, 2], 0))), 2)
                st["net_approach_frac"] = round(float(np.mean(arr[:, 2] > NET_Y_M - 3.5)), 2)
            st["suspect"] = bool(st["peak_speed_ms"] > 12)  # faster than elite sprinting => tracking noise
            draw_court_heatmap(arr[:, 1:3], outdir / f"heatmap_{side}.png", f"{side} player coverage")
            st["heatmap"] = f"match/heatmap_{side}.png"
            players[side] = st

    result = {"available": True, "device": device,
              "court_median_valid_kps": med_valid, "n_homographies": len(homos),
              "analyzed_seconds": round(dur, 1), "players": players}

    if args.with_ball:
        tp = VENDOR / "TennisProject"
        weights = {k: MODELS / f for k, f in
                   [("ball", "tracknet_ball.pt"), ("court", "court_detector.pt"), ("bounce", "bounce_catboost.cbm")]}
        if tp.is_dir() and all(p.exists() for p in weights.values()):
            tmp720 = outdir / "_tmp_720p.mp4"
            out_vid = outdir / "ball_annotated.mp4"
            try:
                subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vf", "scale=1280:720",
                                "-t", str(int(dur)), "-an", str(tmp720)],
                               check=True, capture_output=True)
                r = subprocess.run([sys.executable, "main.py",
                                    "--path_ball_track_model", str(weights["ball"]),
                                    "--path_court_model", str(weights["court"]),
                                    "--path_bounce_model", str(weights["bounce"]),
                                    "--path_input_video", str(tmp720),
                                    "--path_output_video", str(out_vid)],
                                   cwd=tp, capture_output=True, text=True, timeout=3600)
                result["ball_pipeline"] = {"ok": r.returncode == 0 and out_vid.exists(),
                                           "output": str(out_vid) if out_vid.exists() else None,
                                           "stderr_tail": r.stderr[-500:] if r.returncode else None}
            except Exception as e:
                result["ball_pipeline"] = {"ok": False, "error": str(e)[:300]}
            finally:
                tmp720.unlink(missing_ok=True)
        else:
            result["ball_pipeline"] = {"ok": False, "error": "TennisProject vendor or ball/bounce weights missing"}

    (outdir / "match_metrics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "players"} |
                     {"players": {s: {kk: players[s][kk] for kk in
                                      ("distance_m", "avg_moving_speed_ms", "peak_speed_ms", "net_approach_frac")}
                                  for s in players}}, indent=2))


if __name__ == "__main__":
    main()
