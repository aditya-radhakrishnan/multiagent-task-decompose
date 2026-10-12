"""
Stage 3: Visualize
Builds tables + charts from experiments/outputs (cost/tokens/time) and experiments/evaluations/<version> (scores).
Writes experiments/visualizations/<version>/report.html and report.md. No API calls; instant to re-run.

Examples:
  python src/visualize_experiments.py
  python src/visualize_experiments.py --version v2_tweaked --tasks api_endpoint,ecommerce
"""

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPROACHES = ["single_agent", "parallel_multi", "best_of_n"]
LABELS = {"single_agent": "Single Agent", "parallel_multi": "Parallel Multi-Agent", "best_of_n": "Best-of-N"}
COLORS = {"single_agent": "#2a6fdb", "parallel_multi": "#d9822b", "best_of_n": "#2e9e6b"}


def load(path: Path):
    with open(path) as f:
        return json.load(f)


def collect(version: str, task_filter):
    tasks = load(ROOT / "tasks.json")["tasks"]
    eval_dir = ROOT / "experiments" / "evaluations" / version
    if not eval_dir.exists():
        raise SystemExit(f"No evaluations at {eval_dir}. Run evaluate_experiments.py first.")
    rows = []
    for tid, t in tasks.items():
        if task_filter and tid not in task_filter:
            continue
        ef = eval_dir / f"{tid}.json"
        if not ef.exists():
            continue
        ev = load(ef)
        row = {"id": tid, "name": t["name"], "complexity": t["complexity"], "approaches": {}}
        for a in APPROACHES:
            of = ROOT / "experiments" / "outputs" / tid / f"{a}.json"
            if a not in ev or not of.exists():
                continue
            ex = load(of)["execution"]
            if a == "best_of_n":
                duration = sum(x.get("duration_seconds", 0) for x in ex["attempts"])
            else:
                duration = ex.get("duration_seconds")
            row["approaches"][a] = {
                "score": ev[a]["score"], "total": ev[a]["total"],
                "requirements": ev[a]["requirements"],
                "tokens": ex["total_tokens"], "cost": ex["cost_usd"], "duration": duration,
                "extra": {k: ev[a][k] for k in ("selected_attempt", "n", "mean_attempt_score") if k in ev[a]},
                "truncated_for_grader": ev[a].get("truncated_for_grader", False),
            }
        rows.append(row)
    return rows


def fmt(v, kind):
    if v is None:
        return "n/a"
    return {"cost": f"${v:.2f}", "tokens": f"{v:,}", "time": f"{v:,.0f}s", "score": f"{v}"}[kind]


def markdown(rows, version):
    out = [f"# Results ({version})", ""]
    for title, key, kind in [("Checklist score (out of 12)", "score", "score"), ("Cost (USD)", "cost", "cost"),
                             ("Total tokens", "tokens", "tokens"), ("Wall-clock time (best-of-N = summed attempts)", "duration", "time")]:
        out += [f"## {title}", "", "| Task | " + " | ".join(LABELS[a] for a in APPROACHES) + " |", "|---|" + "---|" * len(APPROACHES)]
        for r in rows:
            cells = [fmt(r["approaches"].get(a, {}).get(key), kind) for a in APPROACHES]
            out.append(f"| {r['name']} ({r['complexity']}) | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


def build_html(rows, version):
    def table(title, key, kind, note=""):
        h = f"<h2>{title}</h2>" + (f"<p class='note'>{note}</p>" if note else "")
        h += "<table><tr><th>Task</th>" + "".join(f"<th>{LABELS[a]}</th>" for a in APPROACHES) + "</tr>"
        for r in rows:
            h += f"<tr><td>{html.escape(r['name'])} <span class='tag'>{r['complexity']}</span></td>"
            for a in APPROACHES:
                d = r["approaches"].get(a)
                cell = fmt(d[key], kind) if d else "n/a"
                if d and key == "score":
                    cell += f" / {d['total']}"
                    if d["extra"]:
                        cell += f" <span class='tag'>N={d['extra']['n']}, mean {d['extra']['mean_attempt_score']}</span>"
                h += f"<td>{cell}</td>"
            h += "</tr>"
        return h + "</table>"

    # Per-item pass rate table
    items = list(next(iter(rows[0]["approaches"].values()))["requirements"].keys()) if rows and rows[0]["approaches"] else []
    h_items = "<h2>Checklist items passed (count across tasks)</h2><table><tr><th>Item</th>" + "".join(f"<th>{LABELS[a]}</th>" for a in APPROACHES) + "</tr>"
    for it in items:
        h_items += f"<tr><td>{it.replace('_', ' ')}</td>"
        for a in APPROACHES:
            have = [r["approaches"][a] for r in rows if a in r["approaches"]]
            h_items += f"<td>{sum(1 for d in have if d['requirements'].get(it))} / {len(have)}</td>"
        h_items += "</tr>"
    h_items += "</table>"

    # Averages
    h_avg = "<h2>Averages across tasks</h2><table><tr><th>Approach</th><th>Mean score /12</th><th>Mean cost</th><th>Mean time</th><th>Score per $</th></tr>"
    for a in APPROACHES:
        ds = [r["approaches"][a] for r in rows if a in r["approaches"]]
        if not ds:
            continue
        ms = sum(d["score"] for d in ds) / len(ds)
        mc = sum(d["cost"] for d in ds) / len(ds)
        times = [d["duration"] for d in ds if d["duration"] is not None]
        mt = sum(times) / len(times) if times else None
        h_avg += f"<tr><td>{LABELS[a]}</td><td>{ms:.1f}</td><td>${mc:.2f}</td><td>{fmt(mt, 'time')}</td><td>{ms / mc:.1f}</td></tr>"
    h_avg += "</table>"

    warn = any(d["truncated_for_grader"] for r in rows for d in r["approaches"].values())
    warn_html = "<p class='note'>Some outputs exceeded the grader's character limit and were truncated.</p>" if warn else ""

    labels = [r["name"] for r in rows]
    def ds(key):
        return [{"label": LABELS[a], "backgroundColor": COLORS[a],
                 "data": [r["approaches"].get(a, {}).get(key) for r in rows]} for a in APPROACHES]

    data = json.dumps({"labels": labels, "score": ds("score"), "duration": ds("duration"), "tokens": ds("tokens")})
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Multi-Agent Results</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
body{{font-family:system-ui,sans-serif;max-width:980px;margin:0 auto;padding:24px 16px;color:#1b1f24;background:#fff}}
section{{border:1px solid #d0d7de;border-radius:8px;padding:8px 20px 20px;margin:20px 0}}
table{{border-collapse:collapse;width:100%;margin:8px 0;font-size:14px}}
th,td{{border-bottom:1px solid #e5e8eb;padding:8px;text-align:left}}th{{background:#f6f8fa}}
.tag{{font-size:11px;color:#57606a;background:#eef1f4;border-radius:4px;padding:1px 6px;margin-left:4px}}
.note{{color:#57606a;font-size:13px}}canvas{{max-height:320px}}
</style></head><body>
<h1>Single vs Parallel Multi-Agent vs Best-of-N</h1>
<p class="note">Evaluation set: {html.escape(version)} · {len(rows)} tasks · score = binary checklist items met out of 12</p>{warn_html}
<section>{h_avg}</section>
<section><h2>Checklist score by task</h2><canvas id="c1"></canvas></section>
<section>{table("Checklist score", "score", "score")}</section>
<section>{table("Cost", "cost", "cost")}</section>
<section>{table("Total tokens", "tokens", "tokens")}</section>
<section><h2>Wall-clock time by task</h2><canvas id="c2"></canvas>
{table("Time", "duration", "time", "Best-of-N time is the sum of its sequential attempts. Single agent and best-of-N times depend on how they were run.")}</section>
<section>{h_items}</section>
<script>
const D={data};
const opts=(t)=>({{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{beginAtZero:true,title:{{display:true,text:t}}}}}}}});
new Chart(document.getElementById('c1'),{{type:'bar',data:{{labels:D.labels,datasets:D.score}},options:{{...opts('Score (of 12)'),scales:{{y:{{beginAtZero:true,max:12,title:{{display:true,text:'Score (of 12)'}}}}}}}}}});
new Chart(document.getElementById('c2'),{{type:'bar',data:{{labels:D.labels,datasets:D.duration}},options:opts('Seconds')}});
</script></body></html>"""


def main():
    p = argparse.ArgumentParser(description="Generate tables and graphs")
    p.add_argument("--version", default="binary_checklist_v1")
    p.add_argument("--tasks", default="all")
    args = p.parse_args()
    flt = None if args.tasks == "all" else set(args.tasks.split(","))
    rows = collect(args.version, flt)
    if not rows:
        raise SystemExit("Nothing to visualize yet.")
    out = ROOT / "experiments" / "visualizations" / args.version
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.html").write_text(build_html(rows, args.version))
    (out / "report.md").write_text(markdown(rows, args.version))
    print(f"Wrote {out / 'report.html'}\nWrote {out / 'report.md'}")


if __name__ == "__main__":
    main()
