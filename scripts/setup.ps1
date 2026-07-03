# Windows setup for tennis-video-analysis. Idempotent - safe to re-run.
# Mirrors setup.sh:  .\setup.ps1 status | basic | full
# Data home: $env:TENNIS_ANALYSIS_HOME (default %USERPROFILE%\.tennis-analysis)
# Requires: Python 3.10+ on PATH (python or py launcher). ffmpeg via winget if absent.

param([ValidateSet("status", "basic", "full")][string]$Mode = "status")

$TennisHome = if ($env:TENNIS_ANALYSIS_HOME) { $env:TENNIS_ANALYSIS_HOME } else { Join-Path $env:USERPROFILE ".tennis-analysis" }
$Venv   = Join-Path $TennisHome "venv"
$Vendor = Join-Path $TennisHome "vendor"
$Models = Join-Path $TennisHome "models"
$Py     = Join-Path $Venv "Scripts\python.exe"

$BasicPkgs = @("numpy", "opencv-python", "mediapipe")
$FullPkgs  = @("torch", "torchvision", "ultralytics", "catboost", "pandas", "scipy", "gdown")

$PoseModelUrl = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"

# name = drive file id, filename, source repo
$Weights = @(
    @{Id = "1f-Co64ehgq4uddcQm1aFBDtbnyZhQvgG"; File = "court_detector.pt";   Src = "yastrebksv/TennisCourtDetector"},
    @{Id = "1XEYZ4myUN7QT-NeBYJI0xteLsvs-ZAOl"; File = "tracknet_ball.pt";    Src = "yastrebksv/TrackNet"},
    @{Id = "1Eo5HDnAQE8y_FbOftKZ8pjiojwuy2BmJ"; File = "bounce_catboost.cbm"; Src = "yastrebksv/TennisProject"},
    @{Id = "1UZwiG1jkWgce9lNhxJ2L0NVjX1vGM05U"; File = "ball_yolov5.pt";      Src = "abdullahtarek/tennis_analysis"},
    @{Id = "1QrTOF1ToQ4plsSZbkBs3zOLkVt3MBlta"; File = "court_kps_cnn.pth";   Src = "abdullahtarek/tennis_analysis"}
)
$Repos = @(
    @{Url = "https://github.com/yastrebksv/TennisProject";       Name = "TennisProject"},
    @{Url = "https://github.com/yastrebksv/TennisCourtDetector"; Name = "TennisCourtDetector"},
    @{Url = "https://github.com/abdullahtarek/tennis_analysis";  Name = "tennis_analysis"}
)

function Ok($msg)   { Write-Host "  [ok]      $msg" }
function Miss($msg) { Write-Host "  [missing] $msg" }
function HavePkg($name) { & $Py -c "import $name" 2>$null; return ($LASTEXITCODE -eq 0) }
function FileOk($path)  { (Test-Path $path) -and ((Get-Item $path).Length -gt 100000) }

function Get-BasePython {
    foreach ($cand in @("python", "py")) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if ($cmd) { if ($cand -eq "py") { return @("py", "-3") } else { return @("python") } }
    }
    return $null
}

function Show-Status {
    Write-Host "tennis-video-analysis setup status (data home: $TennisHome)"
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { Ok "ffmpeg" } else { Miss "ffmpeg (Tier 0)" }
    if (Test-Path $Py) {
        Ok "venv at $Venv"
        if (HavePkg "cv2")         { Ok "opencv" }       else { Miss "opencv (Tier 0-1)" }
        if (HavePkg "mediapipe")   { Ok "mediapipe" }    else { Miss "mediapipe (Tier 1)" }
        if (FileOk (Join-Path $Models "pose_landmarker_lite.task")) { Ok "models/pose_landmarker_lite.task" } else { Miss "models/pose_landmarker_lite.task (Tier 1)" }
        if (HavePkg "torch")       { Ok "torch" }        else { Miss "torch (Tier 2)" }
        if (HavePkg "ultralytics") { Ok "ultralytics" }  else { Miss "ultralytics (Tier 2)" }
        if (HavePkg "catboost")    { Ok "catboost" }     else { Miss "catboost (Tier 2, ball/bounce)" }
    } else { Miss "venv (run: .\setup.ps1 basic)" }
    foreach ($r in $Repos) {
        if (Test-Path (Join-Path $Vendor "$($r.Name)\.git")) { Ok "vendor/$($r.Name)" } else { Miss "vendor/$($r.Name) (Tier 2)" }
    }
    foreach ($w in $Weights) {
        if (FileOk (Join-Path $Models $w.File)) { Ok "models/$($w.File)" } else { Miss "models/$($w.File) ($($w.Src))" }
    }
}

function Install-Ffmpeg {
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { return $true }
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Installing ffmpeg via winget (Gyan.FFmpeg)..."
        winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
        Write-Host "NOTE: open a NEW terminal afterwards so ffmpeg lands on PATH."
        return $true
    }
    Write-Host "ERROR: ffmpeg missing and winget not found. Install from https://www.gyan.dev/ffmpeg/builds/ and add to PATH."
    return $false
}

function Install-Venv {
    New-Item -ItemType Directory -Force -Path $TennisHome | Out-Null
    if (-not (Test-Path $Py)) {
        $base = Get-BasePython
        if (-not $base) { Write-Host "ERROR: no python/py on PATH. Install Python 3.10+ from python.org."; return $false }
        Write-Host "Creating venv at $Venv ..."
        & $base[0] $base[1..($base.Count)] -m venv $Venv
        if (-not (Test-Path $Py)) { return $false }
    }
    & $Py -m pip install --quiet --upgrade pip
    Write-Host "Installing base packages ($($BasicPkgs -join ' '))..."
    & $Py -m pip install --quiet @BasicPkgs
    return $true
}

function Install-PoseModel {
    New-Item -ItemType Directory -Force -Path $Models | Out-Null
    $f = Join-Path $Models "pose_landmarker_lite.task"
    if (FileOk $f) { Ok "pose model already present"; return $true }
    Write-Host "Downloading MediaPipe pose landmarker model..."
    Invoke-WebRequest -Uri $PoseModelUrl -OutFile $f
    return (FileOk $f)
}

function Install-FullPkgs {
    Write-Host "Installing Tier-2 packages ($($FullPkgs -join ' ')) - this downloads ~2GB, be patient..."
    & $Py -m pip install --quiet @FullPkgs
}

function Install-Repos {
    New-Item -ItemType Directory -Force -Path $Vendor | Out-Null
    foreach ($r in $Repos) {
        $dest = Join-Path $Vendor $r.Name
        if (Test-Path (Join-Path $dest ".git")) { Ok "vendor/$($r.Name) already cloned" }
        else { Write-Host "Cloning $($r.Url) ..."; git clone --depth 1 $r.Url $dest }
    }
}

function Install-Weights {
    New-Item -ItemType Directory -Force -Path $Models | Out-Null
    $failures = 0
    foreach ($w in $Weights) {
        $f = Join-Path $Models $w.File
        if (FileOk $f) { Ok "models/$($w.File) already present"; continue }
        Write-Host "Downloading $($w.File) from Google Drive ($($w.Src))..."
        & $Py -m gdown $w.Id -O $f
        if (-not (FileOk $f)) { $failures++; Remove-Item -Force -ErrorAction SilentlyContinue $f; Miss "$($w.File) - gdown failed (Drive quota or link rot)" }
    }
    if ($failures -gt 0) {
        Write-Host ""
        Write-Host "Some weights failed to download automatically. Manual fallback - open each URL,"
        Write-Host "download, and save into $Models with the exact filename:"
        foreach ($w in $Weights) { Write-Host "  $($w.File)  <-  https://drive.google.com/file/d/$($w.Id)/view  ($($w.Src))" }
        Write-Host "Tier 2 stays disabled for any missing weight; Tiers 0-1 are unaffected."
    }
}

switch ($Mode) {
    "status" { Show-Status }
    "basic"  { if ((Install-Ffmpeg) -and (Install-Venv) -and (Install-PoseModel)) { Write-Host "Basic setup done (Tiers 0-1)." }; Show-Status }
    "full"   { if ((Install-Ffmpeg) -and (Install-Venv) -and (Install-PoseModel)) { Install-FullPkgs; Install-Repos; Install-Weights; Write-Host "Full setup done." }; Show-Status }
}
