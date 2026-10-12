"""
Stage 2: Evaluate
Grades raw outputs from experiments/outputs/ and writes experiments/evaluations/<version>/<task>.json.
Re-runnable without re-running any task. Use --version to keep several grader runs side by side.

Examples:
  python src/evaluate_experiments.py
  python src/evaluate_experiments.py --tasks api_endpoint,ecommerce --overwrite
  python src/evaluate_experiments.py --grader binary_checklist --version v2_tweaked
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

APPROACHES = ["single_agent", "parallel_multi", "best_of_n"]


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def parallel_text(execution: dict) -> str:
    """Combine all subtask state files into the single deliverable that gets graded."""
    outputs = execution.get("subtask_outputs", {})
    return "\n\n".join(f"===== {name} =====\n{text}" for name, text in sorted(outputs.items()))


def evaluate_task(grader, task: dict, task_dir: Path) -> dict:
    desc = task["description"]
    result = {"task_id": task["id"], "grader": grader.GRADER_VERSION}

    f = task_dir / "single_agent.json"
    if f.exists():
        d = load_json(f)
        result["single_agent"] = grader.evaluate_output(desc, d["execution"]["output"], "Single Agent")

    f = task_dir / "parallel_multi.json"
    if f.exists():
        d = load_json(f)
        result["parallel_multi"] = grader.evaluate_output(desc, parallel_text(d["execution"]), "Parallel Multi-Agent")

    f = task_dir / "best_of_n.json"
    if f.exists():
        d = load_json(f)
        scored = []
        for a in d["execution"]["attempts"]:
            g = grader.evaluate_output(desc, a["output"], f"Best-of-N attempt {a['attempt_number']}")
            g["attempt_number"] = a["attempt_number"]
            scored.append(g)
        best = max(scored, key=lambda g: (g["score"], -g["attempt_number"]))  # ties -> earliest
        result["best_of_n"] = {
            **best,
            "selected_attempt": best["attempt_number"],
            "n": len(scored),
            "all_attempt_scores": [g["score"] for g in scored],
            "mean_attempt_score": round(sum(g["score"] for g in scored) / len(scored), 2),
        }
    return result


def main():
    p = argparse.ArgumentParser(description="Grade experiment outputs")
    p.add_argument("--grader", default="binary_checklist", help="module name in src/graders/")
    p.add_argument("--version", default=None, help="evaluation folder name (default: grader's version string)")
    p.add_argument("--tasks", default="all")
    p.add_argument("--overwrite", action="store_true", help="re-grade tasks that already have an evaluation")
    args = p.parse_args()

    grader = importlib.import_module(f"graders.{args.grader}")
    version = args.version or grader.GRADER_VERSION
    tasks = load_json(ROOT / "tasks.json")["tasks"]
    ids = list(tasks) if args.tasks == "all" else args.tasks.split(",")

    out_dir = ROOT / "experiments" / "evaluations" / version
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Grader: {args.grader} | evaluation set: {version}")

    for tid in ids:
        if tid not in tasks:
            print(f"  ! unknown task {tid}, skipping")
            continue
        task_dir = ROOT / "experiments" / "outputs" / tid
        if not task_dir.exists():
            print(f"  - {tid}: no outputs yet, skipping")
            continue
        out_file = out_dir / f"{tid}.json"
        if out_file.exists() and not args.overwrite:
            print(f"  - {tid}: already graded (use --overwrite)")
            continue
        print(f"\n== {tid}")
        res = evaluate_task(grader, tasks[tid], task_dir)
        with open(out_file, "w") as f:
            json.dump(res, f, indent=2)
        for a in APPROACHES:
            if a in res:
                print(f"  {a}: {res[a]['score']}/{res[a]['total']}")

    print(f"\nSaved to {out_dir}\nNext: python src/visualize_experiments.py --version {version}")


if __name__ == "__main__":
    main()
