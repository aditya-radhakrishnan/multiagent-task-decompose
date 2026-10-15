"""
Stage 2 (pairwise): grade single agent vs multi-agent side by side, per run.

Uses the paper's rubric (completeness, correctness, code quality, consistency; 1-10 each).
Fixes from the v1 grader:
  - the grader sees the full outputs (v1 cut them to a few thousand characters)
  - approach names are removed and state-file markers stripped
  - each pair is graded in both orders, `--samples` times per order, to average out position bias
  - unparseable responses are reported and excluded, not scored as zero

Writes experiments/evaluations/<version>/<task>/run_<k>.json and prints a summary.

Example:
  python src/grade_pairwise.py --tasks api_endpoint,ecommerce --samples 2
"""

import argparse
import json
import os
import re
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
GRADER = "claude-opus-5-5"
PRICE = (4.0, 20.0)  # USD per 1M input / output tokens
CRITERIA = ["completeness", "correctness", "code_quality", "consistency"]

PROMPT = """You are comparing two implementations of the same software engineering task.

TASK:
{task}

---

# APPROACH 1

{first}

---

# APPROACH 2

{second}

---

# EVALUATION CRITERIA

Score each approach from 1-10 on:

1. **Completeness**: Are all required components present and functional?
2. **Correctness**: Does the implementation actually work? Are there bugs or issues?
3. **Code Quality**: Error handling, structure, readability, production-readiness
4. **Consistency**: If multiple components, do they align properly?

Briefly justify each score with specific evidence from the code, then say which approach produced the better implementation overall.

End your response with a JSON block in exactly this format (integer scores 1-10):

```json
{{"approach_1": {{"completeness": 0, "correctness": 0, "code_quality": 0, "consistency": 0}},
 "approach_2": {{"completeness": 0, "correctness": 0, "code_quality": 0, "consistency": 0}},
 "winner": "approach_1 or approach_2"}}
```"""


def multi_agent_text(execution: dict) -> str:
    """Join subtask outputs, dropping the '# Subtask X State' header, timestamp and STATUS line."""
    parts = []
    for i, (_, text) in enumerate(sorted(execution["subtask_outputs"].items()), 1):
        text = re.sub(r"\A# Subtask \w+ State\nLast Updated:.*?\n\n", "", text)
        text = re.sub(r"\n*STATUS: \w+\s*\Z", "\n", text)
        parts.append(f"## Part {i}\n\n{text}")
    return "\n\n".join(parts)


def parse_scores(text: str):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if not blocks:
        return None
    try:
        data = json.loads(blocks[-1])
        return {k: {c: int(data[k][c]) for c in CRITERIA} for k in ("approach_1", "approach_2")}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def grade(client, prompt: str):
    with client.messages.stream(model=GRADER, max_tokens=16000,
                                messages=[{"role": "user", "content": prompt}]) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        return None, "", 0.0
    text = "".join(b.text for b in msg.content if b.type == "text")
    cost = msg.usage.input_tokens / 1e6 * PRICE[0] + msg.usage.output_tokens / 1e6 * PRICE[1]
    return parse_scores(text), text, cost


def main():
    p = argparse.ArgumentParser(description="Pairwise grading of single vs multi-agent outputs")
    p.add_argument("--tasks", default="api_endpoint,ecommerce")
    p.add_argument("--samples", type=int, default=2, help="gradings per order per run")
    p.add_argument("--version", default="pairwise_opus55")
    p.add_argument("--max-cost", type=float, default=8.0)
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    tasks = json.loads((ROOT / "tasks.json").read_text())["tasks"]
    spent = 0.0

    for task_id in args.tasks.split(","):
        for run_dir in sorted((ROOT / "experiments/outputs" / task_id).glob("run_*")):
            single_f, multi_f = run_dir / "single_agent.json", run_dir / "parallel_multi.json"
            if not (single_f.exists() and multi_f.exists()):
                continue
            out = ROOT / "experiments/evaluations" / args.version / task_id / f"{run_dir.name}.json"
            if out.exists() and not args.overwrite:
                print(f"{task_id} {run_dir.name}: already graded")
                continue
            single = json.loads(single_f.read_text())["execution"]["output"]
            multi = multi_agent_text(json.loads(multi_f.read_text())["execution"])
            gradings = []
            for order in ("single_first", "multi_first"):
                first, second = (single, multi) if order == "single_first" else (multi, single)
                prompt = PROMPT.format(task=tasks[task_id]["description"], first=first, second=second)
                for s in range(args.samples):
                    if spent >= args.max_cost:
                        raise SystemExit(f"Cost cap ${args.max_cost:.2f} reached (spent ${spent:.2f})")
                    scores, text, cost = grade(client, prompt)
                    spent += cost
                    if scores is None:
                        print(f"  {task_id} {run_dir.name} {order} #{s}: unparseable, excluded")
                        gradings.append({"order": order, "sample": s, "scores": None, "raw": text})
                        continue
                    s_sc, m_sc = ((scores["approach_1"], scores["approach_2"]) if order == "single_first"
                                  else (scores["approach_2"], scores["approach_1"]))
                    gradings.append({"order": order, "sample": s, "single": s_sc, "multi": m_sc,
                                     "single_total": sum(s_sc.values()), "multi_total": sum(m_sc.values()),
                                     "raw": text})
                    print(f"  {task_id} {run_dir.name} {order} #{s}: single {sum(s_sc.values())}/40, "
                          f"multi {sum(m_sc.values())}/40  (${cost:.2f})")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"task_id": task_id, "run": run_dir.name, "grader": GRADER,
                                       "gradings": gradings}, indent=2))

    print(f"\nSpent ${spent:.2f}\n")
    print(f"{'task':<14} {'runs':>4} {'gradings':>8}  {'single mean':>11}  {'multi mean':>10}")
    for task_id in args.tasks.split(","):
        files = sorted((ROOT / "experiments/evaluations" / args.version / task_id).glob("run_*.json"))
        gs = [g for f in files for g in json.loads(f.read_text())["gradings"] if g.get("single")]
        if gs:
            print(f"{task_id:<14} {len(files):>4} {len(gs):>8}  "
                  f"{sum(g['single_total'] for g in gs) / len(gs):>11.1f}  "
                  f"{sum(g['multi_total'] for g in gs) / len(gs):>10.1f}")


if __name__ == "__main__":
    main()
