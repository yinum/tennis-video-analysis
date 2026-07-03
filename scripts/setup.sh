#!/usr/bin/env bash
# Setup for tennis-video-analysis. Idempotent — safe to re-run; it fills in whatever
# is missing. Heavy artifacts live in the data home, never in the skill directory.
#
# Usage:
#   setup.sh status          # report what is installed / missing (no changes)
#   setup.sh basic           # ffmpeg + venv with OpenCV/MediaPipe  (Tiers 0–1)
#   setup.sh full            # basic + torch/ultralytics/catboost, vendor repos, weights (Tier 2)
#
# Data home: $TENNIS_ANALYSIS_HOME (default ~/.tennis-analysis)

set -uo pipefail

TENNIS_HOME="${TENNIS_ANALYSIS_HOME:-$HOME/.tennis-analysis}"
VENV="$TENNIS_HOME/venv"
VENDOR="$TENNIS_HOME/vendor"
MODELS="$TENNIS_HOME/models"
PY="$VENV/bin/python"
MODE="${1:-status}"

BASIC_PKGS="numpy opencv-python mediapipe"
FULL_PKGS="torch torchvision ultralytics catboost pandas scipy gdown"

# model_key|drive_file_id|filename|source
WEIGHTS=(
  "court_detector|1f-Co64ehgq4uddcQm1aFBDtbnyZhQvgG|court_detector.pt|yastrebksv/TennisCourtDetector"
  "tracknet_ball|1XEYZ4myUN7QT-NeBYJI0xteLsvs-ZAOl|tracknet_ball.pt|yastrebksv/TrackNet"
  "bounce_catboost|1Eo5HDnAQE8y_FbOftKZ8pjiojwuy2BmJ|bounce_catboost.cbm|yastrebksv/TennisProject"
  "ball_yolov5|1UZwiG1jkWgce9lNhxJ2L0NVjX1vGM05U|ball_yolov5.pt|abdullahtarek/tennis_analysis"
  "court_kps_cnn|1QrTOF1ToQ4plsSZbkBs3zOLkVt3MBlta|court_kps_cnn.pth|abdullahtarek/tennis_analysis"
)

REPOS=(
  "https://github.com/yastrebksv/TennisProject|TennisProject"
  "https://github.com/yastrebksv/TennisCourtDetector|TennisCourtDetector"
  "https://github.com/abdullahtarek/tennis_analysis|tennis_analysis"
)

POSE_MODEL_URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"

say()  { printf '%s\n' "$*"; }
ok()   { printf '  [ok]      %s\n' "$*"; }
miss() { printf '  [missing] %s\n' "$*"; }

have_pkg() { "$PY" -c "import $1" >/dev/null 2>&1; }

status() {
  say "tennis-video-analysis setup status (data home: $TENNIS_HOME)"
  command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')" || miss "ffmpeg (Tier 0)"
  if [ -x "$PY" ]; then
    ok "venv at $VENV"
    have_pkg cv2       && ok "opencv"    || miss "opencv (Tier 0-1)"
    have_pkg mediapipe && ok "mediapipe" || miss "mediapipe (Tier 1)"
    [ -f "$MODELS/pose_landmarker_lite.task" ] && ok "models/pose_landmarker_lite.task" \
      || miss "models/pose_landmarker_lite.task (Tier 1)"
    have_pkg torch     && ok "torch"     || miss "torch (Tier 2)"
    have_pkg ultralytics && ok "ultralytics" || miss "ultralytics (Tier 2)"
    have_pkg catboost  && ok "catboost"  || miss "catboost (Tier 2, ball/bounce)"
  else
    miss "venv (run: setup.sh basic)"
  fi
  for spec in "${REPOS[@]}"; do
    name="${spec#*|}"
    [ -d "$VENDOR/$name/.git" ] && ok "vendor/$name" || miss "vendor/$name (Tier 2)"
  done
  for spec in "${WEIGHTS[@]}"; do
    IFS='|' read -r key id fname src <<<"$spec"
    f="$MODELS/$fname"
    # >1MB guard: gdown quota failures leave tiny HTML files behind
    if [ -f "$f" ] && [ "$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f")" -gt 1000000 ]; then
      ok "models/$fname"
    else
      miss "models/$fname ($src)"
    fi
  done
}

install_ffmpeg() {
  command -v ffmpeg >/dev/null 2>&1 && return 0
  if command -v brew >/dev/null 2>&1; then
    say "Installing ffmpeg via Homebrew..."
    brew install ffmpeg
  else
    say "ERROR: ffmpeg missing and Homebrew not found. Install ffmpeg manually."
    return 1
  fi
}

install_venv() {
  mkdir -p "$TENNIS_HOME"
  if [ ! -x "$PY" ]; then
    say "Creating venv at $VENV ..."
    python3 -m venv "$VENV" || return 1
  fi
  "$PY" -m pip install --quiet --upgrade pip
  say "Installing base packages ($BASIC_PKGS)..."
  "$PY" -m pip install --quiet $BASIC_PKGS
}

install_pose_model() {
  mkdir -p "$MODELS"
  f="$MODELS/pose_landmarker_lite.task"
  if [ -f "$f" ] && [ "$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f")" -gt 1000000 ]; then
    ok "pose model already present"
  else
    say "Downloading MediaPipe pose landmarker model..."
    curl -sL -o "$f" "$POSE_MODEL_URL" || { miss "pose model download failed"; return 1; }
  fi
}

install_full_pkgs() {
  say "Installing Tier-2 packages ($FULL_PKGS) — this downloads ~2GB, be patient..."
  "$PY" -m pip install --quiet $FULL_PKGS
}

install_repos() {
  mkdir -p "$VENDOR"
  for spec in "${REPOS[@]}"; do
    url="${spec%%|*}"; name="${spec#*|}"
    if [ -d "$VENDOR/$name/.git" ]; then
      ok "vendor/$name already cloned"
    else
      say "Cloning $url ..."
      git clone --depth 1 "$url" "$VENDOR/$name"
    fi
  done
}

install_weights() {
  mkdir -p "$MODELS"
  local failures=0
  for spec in "${WEIGHTS[@]}"; do
    IFS='|' read -r key id fname src <<<"$spec"
    f="$MODELS/$fname"
    if [ -f "$f" ] && [ "$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f")" -gt 1000000 ]; then
      ok "models/$fname already present"
      continue
    fi
    say "Downloading $fname from Google Drive ($src)..."
    if ! "$VENV/bin/gdown" --id "$id" -O "$f"; then
      failures=$((failures+1))
      rm -f "$f"
      miss "$fname — gdown failed (Drive quota or link rot)"
    fi
  done
  if [ "$failures" -gt 0 ]; then
    say ""
    say "Some weights failed to download automatically. Manual fallback:"
    say "open each URL in a browser, download, and save into $MODELS/ with the exact filename:"
    for spec in "${WEIGHTS[@]}"; do
      IFS='|' read -r key id fname src <<<"$spec"
      say "  $fname  <-  https://drive.google.com/file/d/$id/view  ($src)"
    done
    say "Tier 2 stays disabled for any missing weight; Tiers 0-1 are unaffected."
  fi
}

case "$MODE" in
  status) status ;;
  basic)  install_ffmpeg && install_venv && install_pose_model && say "Basic setup done (Tiers 0-1)." && status ;;
  full)   install_ffmpeg && install_venv && install_pose_model && install_full_pkgs && install_repos && install_weights \
            && say "Full setup done." && status ;;
  *) say "Usage: setup.sh {status|basic|full}"; exit 2 ;;
esac
