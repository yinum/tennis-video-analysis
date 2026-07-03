#!/usr/bin/env python
"""Tier 0: sample a tennis video into frames, find high-motion bursts (likely strokes/
rallies), and build timestamped contact sheets so an agent can survey the whole video
in a handful of image loads.

Run with the venv python: ~/.tennis-analysis/venv/bin/python extract_frames.py VIDEO

Outputs into <video_dir>/<stem>_analysis/ (or --outdir):
  meta.json                 video metadata
  frames/f_<t>s.jpg         uniform samples (overview)
  frames/burst_<i>/         dense frames inside each high-motion burst
  sheets/overview_<n>.jpg   tiled overview sheets with timestamps
  sheets/burst_<i>.jpg      one dense sheet per burst (stroke-reading resolution)
  segments.json             burst list with timestamps
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np


def open_video(path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        sys.exit(f"ERROR: cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return cap, {"fps": round(fps, 3), "frame_count": n, "width": w, "height": h,
                 "duration_s": round(n / fps, 2) if fps else None}


def resize_max_w(img, max_w):
    h, w = img.shape[:2]
    if w <= max_w:
        return img
    s = max_w / w
    return cv2.resize(img, (max_w, int(h * s)), interpolation=cv2.INTER_AREA)


def save_jpg(path, img, q=82):
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, q])


def label(img, text):
    img = img.copy()
    cv2.rectangle(img, (0, 0), (10 + 13 * len(text), 26), (0, 0, 0), -1)
    cv2.putText(img, text, (5, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def contact_sheet(images, cols, tile_w):
    """Tile labeled images into a grid; images: list of (text, bgr)."""
    if not images:
        return None
    tiles = []
    th = None
    for text, im in images:
        t = resize_max_w(im, tile_w)
        if th is None:
            th = t.shape[0]
        t = cv2.resize(t, (tile_w, th))
        tiles.append(label(t, text))
    rows = int(np.ceil(len(tiles) / cols))
    blank = np.zeros_like(tiles[0])
    tiles += [blank] * (rows * cols - len(tiles))
    return np.vstack([np.hstack(tiles[r * cols:(r + 1) * cols]) for r in range(rows)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--sample-fps", type=float, default=2.0)
    ap.add_argument("--max-samples", type=int, default=400)
    ap.add_argument("--bursts", type=int, default=6)
    ap.add_argument("--burst-seconds", type=float, default=2.5)
    ap.add_argument("--burst-fps", type=float, default=8.0)
    ap.add_argument("--sheet-cols", type=int, default=5)
    args = ap.parse_args()

    video = Path(args.video).expanduser().resolve()
    out = Path(args.outdir) if args.outdir else video.parent / f"{video.stem}_analysis"
    frames_dir, sheets_dir = out / "frames", out / "sheets"
    frames_dir.mkdir(parents=True, exist_ok=True)
    sheets_dir.mkdir(parents=True, exist_ok=True)

    cap, meta = open_video(video)
    meta["video"] = str(video)
    dur = meta["duration_s"] or 0
    step = max(1, int(round((meta["fps"] or 30) / args.sample_fps)))
    if meta["frame_count"] and meta["frame_count"] / step > args.max_samples:
        step = int(np.ceil(meta["frame_count"] / args.max_samples))

    # Pass 1: uniform samples + per-sample motion score
    samples, motions, prev_small = [], [], None
    idx = 0
    while True:
        ret = cap.grab()
        if not ret:
            break
        if idx % step == 0:
            ret, frame = cap.retrieve()
            if not ret:
                break
            t = idx / meta["fps"]
            small = cv2.cvtColor(resize_max_w(frame, 160), cv2.COLOR_BGR2GRAY)
            m = float(np.mean(cv2.absdiff(small, prev_small))) if prev_small is not None else 0.0
            prev_small = small
            fname = frames_dir / f"f_{t:08.2f}s.jpg"
            save_jpg(fname, resize_max_w(frame, 960))
            samples.append((t, fname.name))
            motions.append(m)
        idx += 1

    if not samples:
        sys.exit("ERROR: no frames decoded — is this a valid video file?")

    # Burst selection: non-overlapping windows around motion peaks
    mo = np.array(motions)
    if len(mo) > 4:
        mo = np.convolve(mo, np.ones(3) / 3, mode="same")
    order = np.argsort(mo)[::-1]
    half = args.burst_seconds / 2
    bursts, taken = [], []
    for i in order:
        t = samples[i][0]
        if any(abs(t - c) < args.burst_seconds * 1.5 for c in taken):
            continue
        taken.append(t)
        bursts.append({"index": len(bursts), "center_s": round(t, 2),
                       "start_s": round(max(0, t - half), 2),
                       "end_s": round(min(dur or t + half, t + half), 2),
                       "motion": round(float(mo[i]), 2)})
        if len(bursts) >= args.bursts:
            break
    bursts.sort(key=lambda b: b["start_s"])
    for k, b in enumerate(bursts):
        b["index"] = k

    # Pass 2: dense frames per burst + one sheet per burst
    for b in bursts:
        bdir = frames_dir / f"burst_{b['index']}"
        bdir.mkdir(exist_ok=True)
        tiles = []
        n_frames = int(args.burst_fps * (b["end_s"] - b["start_s"])) or 1
        for j in range(n_frames):
            t = b["start_s"] + j / args.burst_fps
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ret, frame = cap.read()
            if not ret:
                continue
            fname = bdir / f"b{b['index']}_{t:08.2f}s.jpg"
            save_jpg(fname, resize_max_w(frame, 1280), q=88)
            tiles.append((f"{t:.2f}s", frame))
        sheet = contact_sheet(tiles, args.sheet_cols, tile_w=480)
        if sheet is not None:
            save_jpg(sheets_dir / f"burst_{b['index']}.jpg", sheet, q=85)
            b["sheet"] = f"sheets/burst_{b['index']}.jpg"
            b["frames_dir"] = f"frames/burst_{b['index']}"

    # Overview sheets from uniform samples (cap ~3 sheets of 5x6)
    per_sheet = args.sheet_cols * 6
    max_tiles = per_sheet * 3
    stride = max(1, int(np.ceil(len(samples) / max_tiles)))
    picked = samples[::stride]
    sheet_files = []
    for s_i in range(0, len(picked), per_sheet):
        chunk = picked[s_i:s_i + per_sheet]
        tiles = []
        for t, name in chunk:
            im = cv2.imread(str(frames_dir / name))
            if im is not None:
                tiles.append((f"{t:.1f}s", im))
        sheet = contact_sheet(tiles, args.sheet_cols, tile_w=400)
        if sheet is not None:
            fn = sheets_dir / f"overview_{s_i // per_sheet + 1}.jpg"
            save_jpg(fn, sheet, q=85)
            sheet_files.append(f"sheets/{fn.name}")

    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out / "segments.json").write_text(json.dumps(
        {"bursts": bursts, "overview_sheets": sheet_files,
         "sample_step_frames": step, "n_samples": len(samples)}, indent=2), encoding="utf-8")
    cap.release()
    print(json.dumps({"outdir": str(out), "n_samples": len(samples),
                      "n_bursts": len(bursts), "overview_sheets": sheet_files,
                      "burst_sheets": [b.get("sheet") for b in bursts]}, indent=2))


if __name__ == "__main__":
    main()
