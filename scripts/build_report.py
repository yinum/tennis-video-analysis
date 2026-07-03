#!/usr/bin/env python
"""Turn an agent-authored assessment.json (plus whatever tier outputs exist) into the
two deliverables: report.md and a self-contained report.html, and record the session
in the player's history for progress tracking.

Run with any python3 (stdlib only):
  python3 build_report.py ANALYSIS_DIR --player "Name"

Reads from ANALYSIS_DIR: assessment.json (required — schema in SKILL.md), meta.json,
pose/pose_metrics.json, match/match_metrics.json (both optional).
Writes: ANALYSIS_DIR/report.md, ANALYSIS_DIR/report.html.
History: $TENNIS_ANALYSIS_HOME/players/<slug>/history.json (append/replace by dir).
"""
import argparse, base64, html, json, math, os, re, sys
from datetime import date as _date
from pathlib import Path

TENNIS_HOME = Path(os.environ.get("TENNIS_ANALYSIS_HOME", Path.home() / ".tennis-analysis"))
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "report_template.html"

DIM_SHORT = {"serve": "Serve", "return": "Return", "forehand": "Forehand",
             "backhand": "Backhand", "net game": "Net", "movement & footwork": "Movement",
             "rally consistency": "Consistency", "power & spin": "Power",
             "tactics & shot selection": "Tactics", "competitive habits": "Competing"}

REQUIRED = ["player", "date", "stage", "dimensions", "strengths", "weaknesses",
            "style", "development_plan", "caveats"]


def md_lite(text):
    """Minimal markdown -> HTML for assessment prose (bold, italic, bullet lists)."""
    if not text:
        return ""
    out, in_list = [], False
    for line in str(text).split("\n"):
        s = html.escape(line.rstrip())
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        if s.strip().startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{s.strip()[2:]}</li>")
        else:
            if in_list:
                out.append("</ul>"); in_list = False
            if s.strip():
                out.append(f"<p>{s}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def b64_img(path):
    try:
        data = base64.b64encode(Path(path).read_bytes()).decode()
        ext = Path(path).suffix.lstrip(".").lower().replace("jpg", "jpeg")
        return f"data:image/{ext};base64,{data}"
    except Exception:
        return None


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "player"


# ---------- charts (inline SVG, palette roles via CSS vars from the template) ----------

def radar_svg(dims, prev_scores=None, prev_label=None):
    cx, cy, R, n = 230, 200, 148, len(dims)

    def pt(i, val):
        a = -math.pi / 2 + 2 * math.pi * i / n
        r = R * max(0.0, min(val, 10)) / 10
        return cx + r * math.cos(a), cy + r * math.sin(a)

    parts = [f'<svg class="chart" viewBox="0 0 460 430" role="img" aria-label="Skill radar">']
    for lvl in (2, 4, 6, 8, 10):
        ring = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, lvl) for i in range(n)))
        parts.append(f'<polygon points="{ring}" fill="none" stroke="var(--grid)" stroke-width="1"/>')
    for i, d in enumerate(dims):
        x, y = pt(i, 10)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="var(--axis)" stroke-width="1"/>')
        lx, ly = pt(i, 12.2)
        anchor = "middle" if abs(lx - cx) < 12 else ("start" if lx > cx else "end")
        name = DIM_SHORT.get(d["name"].strip().lower(), d["name"][:12])
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="12" '
                     f'fill="var(--ink-2)">{html.escape(name)}</text>')
        parts.append(f'<text x="{lx:.1f}" y="{ly + 13:.1f}" text-anchor="{anchor}" font-size="11" '
                     f'font-weight="600" fill="var(--ink)">{d["score"]:g}</text>')
    if prev_scores:
        prev_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                            (pt(i, prev_scores.get(d["name"], 0)) for i, d in enumerate(dims)))
        parts.append(f'<polygon points="{prev_pts}" fill="none" stroke="var(--muted)" '
                     f'stroke-width="1.6" stroke-dasharray="4 3"/>')
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, d["score"]) for i, d in enumerate(dims)))
    parts.append(f'<polygon points="{poly}" fill="var(--series-1)" fill-opacity="0.18" '
                 f'stroke="var(--series-1)" stroke-width="2"/>')
    for i, d in enumerate(dims):
        x, y = pt(i, d["score"])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--series-1)">'
                     f'<title>{html.escape(d["name"])}: {d["score"]:g}/10</title></circle>')
    if prev_scores and prev_label:
        parts.append(f'<g font-size="11" fill="var(--ink-2)">'
                     f'<line x1="150" y1="424" x2="174" y2="424" stroke="var(--muted)" stroke-width="1.6" stroke-dasharray="4 3"/>'
                     f'<text x="180" y="428">previous session ({html.escape(prev_label)})</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def trend_svg(entries):
    """entries: chronological [{date, ntrp, avg}]. Single-series NTRP line."""
    W, H, ml, mr, mt, mb = 640, 240, 46, 20, 22, 38
    xs = [ml + (W - ml - mr) * (i / max(1, len(entries) - 1)) for i in range(len(entries))]
    vals = [e["ntrp"] for e in entries]
    lo = max(1.0, math.floor((min(vals) - 0.5) * 2) / 2)
    hi = min(7.0, math.ceil((max(vals) + 0.5) * 2) / 2)

    def y(v):
        return mt + (H - mt - mb) * (1 - (v - lo) / max(0.001, hi - lo))

    parts = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="NTRP trend">',
             f'<text x="{ml}" y="14" font-size="12" fill="var(--ink-2)">NTRP estimate across sessions</text>']
    v = lo
    while v <= hi + 1e-9:
        parts.append(f'<line x1="{ml}" y1="{y(v):.1f}" x2="{W - mr}" y2="{y(v):.1f}" '
                     f'stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{ml - 8}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" '
                     f'fill="var(--muted)" style="font-variant-numeric:tabular-nums">{v:g}</text>')
        v += 0.5
    path = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f},{y(vals[i]):.1f}" for i in range(len(entries)))
    parts.append(f'<path d="{path}" fill="none" stroke="var(--series-1)" stroke-width="2"/>')
    for i, e in enumerate(entries):
        parts.append(f'<circle cx="{xs[i]:.1f}" cy="{y(vals[i]):.1f}" r="4.5" fill="var(--series-1)">'
                     f'<title>{e["date"]}: NTRP {e["ntrp"]:g}</title></circle>')
        parts.append(f'<text x="{xs[i]:.1f}" y="{H - 14}" text-anchor="middle" font-size="11" '
                     f'fill="var(--muted)">{html.escape(e["date"][5:] if len(e["date"]) > 7 else e["date"])}</text>')
    parts.append(f'<text x="{xs[-1]:.1f}" y="{y(vals[-1]) - 10:.1f}" text-anchor="middle" font-size="12" '
                 f'font-weight="650" fill="var(--ink)">{vals[-1]:g}</text></svg>')
    return "".join(parts)


# ---------- report assembly ----------

def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_dir")
    ap.add_argument("--player", default=None, help="overrides assessment.json player")
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--publish", default=None, metavar="DIR",
                    help="also copy report.html/.md into DIR (a user-visible folder)")
    args = ap.parse_args()

    adir = Path(args.analysis_dir).expanduser().resolve()
    a = load_json(adir / "assessment.json")
    if a is None:
        sys.exit("ERROR: assessment.json missing or invalid JSON — the agent writes this "
                 "after the vision pass (schema in SKILL.md).")
    if args.player:
        a["player"] = args.player
    missing = [k for k in REQUIRED if k not in a]
    if missing:
        sys.exit(f"ERROR: assessment.json missing keys: {missing}")
    dims = a["dimensions"]
    if len(dims) < 6:
        sys.exit("ERROR: expected the 10 rubric dimensions (got %d)" % len(dims))

    meta = load_json(adir / "meta.json") or {}
    pose = load_json(adir / "pose" / "pose_metrics.json") or {}
    match = load_json(adir / "match" / "match_metrics.json") or {}
    stage = a["stage"]
    avg = round(sum(d["score"] for d in dims) / len(dims), 1)
    today = a.get("date") or _date.today().isoformat()
    tiers = a.get("footage_quality", {}).get("tiers_run", [0])
    video_name = Path(meta.get("video", a.get("video", "unknown"))).name

    # ---- history ----
    prev_scores = prev_label = None
    entries_for_trend = []
    if not args.no_history:
        pdir = TENNIS_HOME / "players" / slugify(a["player"])
        pdir.mkdir(parents=True, exist_ok=True)
        hfile = pdir / "history.json"
        hist = load_json(hfile) or {"player": a["player"], "entries": []}
        entry = {"date": today, "analysis_dir": str(adir), "video": video_name,
                 "ntrp": stage.get("ntrp"), "utr_range": stage.get("utr_range"),
                 "archetype": a["style"].get("archetype"), "avg": avg,
                 "scores": {d["name"]: d["score"] for d in dims},
                 "report": str(adir / "report.html")}
        hist["entries"] = [e for e in hist["entries"] if e.get("analysis_dir") != str(adir)]
        prior = sorted(hist["entries"], key=lambda e: e["date"])
        if prior:
            prev_scores, prev_label = prior[-1]["scores"], prior[-1]["date"]
        hist["entries"] = prior + [entry]
        hfile.write_text(json.dumps(hist, indent=2), encoding="utf-8")
        entries_for_trend = [e for e in hist["entries"] if isinstance(e.get("ntrp"), (int, float))]

    # ---- markdown report ----
    md = [f"# {a['player']} — Player Skill Report", "",
          f"*{today} · {a.get('session_type', 'session')} · video: {video_name} · tiers run: {tiers}*", "",
          f"## Current stage",
          f"**NTRP {stage.get('ntrp', '?')}** (band {stage.get('ntrp_band', '?')}) · "
          f"UTR ~{stage.get('utr_range', '?')} · profile average {avg}/10", "",
          stage.get("justification", ""), "",
          "## Skill profile", "", "| Dimension | Score | Evidence |", "|---|---|---|"]
    md += [f"| {d['name']} | {d['score']:g} | {d.get('evidence', '')} |" for d in dims]
    md += ["", "## Strengths"]
    md += [f"- **{s['title']}** — {s['detail']}" +
           (f" *(evidence: {s['evidence']})*" if s.get("evidence") else "") for s in a["strengths"]]
    md += ["", "## Weaknesses"]
    md += [f"- **{w['title']}** — {w['detail']}" +
           (f" **Fix:** {w['fix']}" if w.get("fix") else "") for w in a["weaknesses"]]
    st = a["style"]
    md += ["", "## Play style & specialties",
           f"**Archetype:** {st.get('archetype', '?')}", ""]
    md += [f"- Resembles **{p['player']}**: {p['why']}" for p in st.get("pro_comparisons", [])]
    if st.get("specialties"):
        md += ["", "Specialties: " + ", ".join(st["specialties"])]
    if a.get("tactics"):
        md += ["", "## Tactics & movement", a["tactics"]]
    for side, p in (match.get("players") or {}).items():
        md += [f"- {side} player: {p['distance_m']} m covered, avg {p['avg_moving_speed_ms']} m/s "
               f"(peak {p['peak_speed_ms']} m/s), at net {int(p.get('net_approach_frac', 0) * 100)}% of samples"
               + (" *(tracking suspect)*" if p.get("suspect") else "")]
    if a.get("history_comparison"):
        md += ["", "## Progress vs. previous sessions", a["history_comparison"]]
    md += ["", "## Development plan"]
    md += [f"{p.get('priority', i + 1)}. **{p['focus']}** — drills: {'; '.join(p.get('drills', []))}. "
           f"Success metric: {p.get('success_metric', 'n/a')}"
           for i, p in enumerate(a["development_plan"])]
    md += ["", "## What this video could not show"]
    md += [f"- {c}" for c in a["caveats"]]
    (adir / "report.md").write_text("\n".join(md), encoding="utf-8")

    # ---- html report ----
    tpl = TEMPLATE.read_text(encoding="utf-8")

    def bar(score):
        return f'<div class="bar"><i style="width:{score * 10:.0f}%"></i></div>'

    dim_rows = "".join(
        f"<tr><td>{html.escape(d['name'])}</td><td class='num'>{d['score']:g}</td><td>{bar(d['score'])}</td></tr>"
        for d in dims)
    strengths = "<ul>" + "".join(
        f"<li><span class='good'>{html.escape(s['title'])}</span> — {html.escape(s['detail'])}"
        + (f"<div class='evidence'>evidence: {html.escape(str(s['evidence']))}</div>" if s.get("evidence") else "")
        + "</li>" for s in a["strengths"]) + "</ul>"
    weaknesses = "<ul>" + "".join(
        f"<li><span class='bad'>{html.escape(w['title'])}</span> — {html.escape(w['detail'])}"
        + (f"<div class='evidence'>fix: {html.escape(str(w['fix']))}</div>" if w.get("fix") else "")
        + "</li>" for w in a["weaknesses"]) + "</ul>"
    style_html = md_lite(st.get("description", "")) + "".join(
        f"<p><strong>{html.escape(p['player'])}</strong> — {html.escape(p['why'])}</p>"
        for p in st.get("pro_comparisons", []))
    if st.get("specialties"):
        style_html += "<div>" + "".join(f"<span class='pill'>{html.escape(s)}</span>"
                                        for s in st["specialties"]) + "</div>"
    plan_html = "<ol>" + "".join(
        f"<li><strong>{html.escape(p['focus'])}</strong><br>drills: {html.escape('; '.join(p.get('drills', [])))}"
        f"<div class='evidence'>success metric: {html.escape(str(p.get('success_metric', 'n/a')))}</div></li>"
        for p in sorted(a["development_plan"], key=lambda p: p.get("priority", 99))) + "</ol>"

    movement = ""
    if a.get("tactics") or match.get("players"):
        movement = "<div class='card'><h2>Tactics &amp; movement</h2>" + md_lite(a.get("tactics", ""))
        rows = ""
        for side, p in (match.get("players") or {}).items():
            rows += (f"<tr><td>{side}</td><td class='num'>{p['distance_m']} m</td>"
                     f"<td class='num'>{p['avg_moving_speed_ms']} m/s</td>"
                     f"<td class='num'>{p['peak_speed_ms']} m/s</td>"
                     f"<td class='num'>{int(p.get('net_approach_frac', 0) * 100)}%</td></tr>")
        if rows:
            movement += ("<table><thead><tr><th>Player</th><th>Distance</th><th>Avg speed</th>"
                         "<th>Peak</th><th>At net</th></tr></thead><tbody>" + rows + "</tbody></table>")
        hm_imgs = ""
        for side in ("near", "far"):
            p = (match.get("players") or {}).get(side, {})
            if p.get("heatmap"):
                src = b64_img(adir / p["heatmap"])
                if src:
                    hm_imgs += (f"<figure><img src='{src}' alt='{side} coverage heatmap'>"
                                f"<figcaption>{side} player court coverage</figcaption></figure>")
        if hm_imgs:
            movement += f"<div class='gallery' style='margin-top:12px'>{hm_imgs}</div>"
        movement += "</div>"

    trend = ""
    if len(entries_for_trend) >= 2:
        trend = ("<div class='card'><h2>Progress across sessions</h2>"
                 + trend_svg(entries_for_trend) + md_lite(a.get("history_comparison", "")) + "</div>")
    elif not args.no_history:
        trend = ("<div class='card'><h2>Progress across sessions</h2><p class='evidence'>"
                 "First session on record — future analyses will chart progress here.</p></div>")

    gallery = ""
    frames = list(a.get("key_frames", []))
    for b in (pose.get("bursts") or []):
        for f in ((b.get("summary") or {}).get("annotated_frames") or []):
            if f not in frames:
                frames.append(f)
    figs = ""
    for f in frames[:8]:
        src = b64_img(adir / f)
        if src:
            figs += (f"<figure><img src='{src}' alt='{html.escape(Path(f).name)}'>"
                     f"<figcaption>{html.escape(Path(f).name)}</figcaption></figure>")
    if figs:
        gallery = f"<div class='card'><h2>Evidence frames</h2><div class='gallery'>{figs}</div></div>"

    subs = {
        "PLAYER": html.escape(a["player"]), "DATE": today,
        "SESSION_META": html.escape(f"{a.get('session_type', 'session')} · "
                                    f"{a.get('footage_quality', {}).get('camera', 'camera unknown')}"),
        "NTRP": f"{stage.get('ntrp', '?')}", "NTRP_BAND": html.escape(str(stage.get("ntrp_band", ""))),
        "UTR": html.escape(str(stage.get("utr_range", "?"))), "AVG_SCORE": f"{avg}",
        "ARCHETYPE": html.escape(str(st.get("archetype", "?"))),
        "HANDEDNESS": html.escape(a.get("handedness") or
                                  (pose.get("handedness_guess") not in (None, "", "unclear", "unknown")
                                   and f"likely {pose['handedness_guess']}-handed" or "")),
        "STAGE_JUSTIFICATION": md_lite(stage.get("justification", "")),
        "RADAR_SVG": radar_svg(dims, prev_scores, prev_label),
        "DIM_ROWS": dim_rows, "STRENGTHS_HTML": strengths, "WEAKNESSES_HTML": weaknesses,
        "STYLE_HTML": style_html, "MOVEMENT_CARD": movement, "TREND_CARD": trend,
        "PLAN_HTML": plan_html, "GALLERY_CARD": gallery,
        "CAVEATS_HTML": "<ul>" + "".join(f"<li>{html.escape(c)}</li>" for c in a["caveats"]) + "</ul>",
        "TIERS": ", ".join(str(t) for t in tiers), "VIDEO_NAME": html.escape(video_name),
    }
    out_html = tpl
    for k, v in subs.items():
        out_html = out_html.replace("{{%s}}" % k, v or "")
    (adir / "report.html").write_text(out_html, encoding="utf-8")

    published = None
    if args.publish:
        pub = Path(args.publish).expanduser()
        pub.mkdir(parents=True, exist_ok=True)
        for f in ("report.html", "report.md"):
            (pub / f).write_bytes((adir / f).read_bytes())
        published = str(pub)

    print(json.dumps({"report_md": str(adir / "report.md"), "report_html": str(adir / "report.html"),
                      "published_to": published,
                      "history_entries": len(entries_for_trend), "avg_score": avg}, indent=2))


if __name__ == "__main__":
    main()
