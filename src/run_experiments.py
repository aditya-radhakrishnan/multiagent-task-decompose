"""
Stage 1: Run Experiments
Executes tasks with different approaches and saves raw outputs to
experiments/outputs/<task>/run_<k>/<approach>.json

Examples:
  python src/run_experiments.py --tasks api_endpoint,ecommerce --approaches single,parallel --runs 3
  python src/run_experiments.py --tasks api_endpoint --runs 1 --max-cost 2   # cheap trial
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent))

from auto_orchestrator import AutoDecomposingOrchestrator

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-5-20250929"
INPUT_PRICE_PER_MILLION = 3.0
OUTPUT_PRICE_PER_MILLION = 15.0

# The paper's v1 run used max_tokens=12000 with a 10,000-token thinking budget, which left the
# single agent ~2,000 tokens of visible output and cut its e-commerce answer off mid-code.
SINGLE_MAX_TOKENS = 32000
THINKING_BUDGET = 10000

PROMPT = """You are tasked with completing the following software engineering task:

TASK:
{task}

Provide a complete implementation. Focus on core functionality and avoid unnecessary extras like extensive deployment documentation or multiple build tool configurations.
"""


def load_tasks():
    with open(Path(__file__).parent.parent / "tasks.json") as f:
        return json.load(f)["tasks"]


def cost_usd(input_tokens: int, output_tokens: int) -> float:
    return input_tokens / 1e6 * INPUT_PRICE_PER_MILLION + output_tokens / 1e6 * OUTPUT_PRICE_PER_MILLION


def call_single(task_description: str) -> dict:
    """One single-agent call with extended thinking. Streams, since max_tokens is large."""
    start = datetime.now()
    with client.messages.stream(
        model=MODEL,
        max_tokens=SINGLE_MAX_TOKENS,
        thinking={"type": "enabled", "budget_tokens": THINKING_BUDGET},
        messages=[{"role": "user", "content": PROMPT.format(task=task_description)}],
    ) as stream:
        message = stream.get_final_message()
    duration = (datetime.now() - start).total_seconds()
    return {
        "output": "".join(b.text for b in message.content if b.type == "text"),
        "stop_reason": message.stop_reason,  # "max_tokens" means the answer was cut off
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "cost_usd": cost_usd(message.usage.input_tokens, message.usage.output_tokens),
        "duration_seconds": duration,
    }


def run_single_agent(task_description: str, task_id: str, output_dir: Path) -> dict:
    print(f"\n== Single agent: {task_id}")
    attempt = call_single(task_description)
    result = {
        "task_id": task_id,
        "approach": "single_agent",
        "timestamp": datetime.now().isoformat(),
        "execution": {**attempt,
                      "total_tokens": attempt["input_tokens"] + attempt["output_tokens"],
                      "model": MODEL},
        "metadata": {"max_tokens": SINGLE_MAX_TOKENS, "extended_thinking": True,
                     "thinking_budget": THINKING_BUDGET},
    }
    with open(output_dir / "single_agent.json", "w") as f:
        json.dump(result, f, indent=2)
    e = result["execution"]
    print(f"   {e['duration_seconds']:.0f}s | {e['total_tokens']:,} tokens | ${e['cost_usd']:.3f} | stop: {e['stop_reason']}")
    return result


def run_parallel_multi_agent(task_description: str, task_id: str, output_dir: Path) -> dict:
    """Auto-decomposition: sub-agents take turns on a shared state directory (not concurrent)."""
    print(f"\n== Multi-agent: {task_id}")
    temp_output = output_dir / "parallel_temp"
    t0 = datetime.now()
    orchestrator = AutoDecomposingOrchestrator(output_dir=str(temp_output), clean_start=True)
    orchestrator.run(task_description, max_iterations=8)
    wall_clock = (datetime.now() - t0).total_seconds()

    with open(temp_output / "debug" / "execution_summary.json") as f:
        summary = json.load(f)
    with open(temp_output / "debug" / "task_decomposition.json") as f:
        decomposition = json.load(f)
    subtask_outputs = {p.name: p.read_text() for p in sorted((temp_output / "state").glob("*.md"))}

    result = {
        "task_id": task_id,
        "approach": "parallel_multi",
        "timestamp": datetime.now().isoformat(),
        "execution": {
            "subtask_outputs": subtask_outputs,
            "decomposition": decomposition,
            "input_tokens": summary["cost_analysis"]["total_input_tokens"],
            "output_tokens": summary["cost_analysis"]["total_output_tokens"],
            "total_tokens": summary["cost_analysis"]["total_tokens"],
            "cost_usd": summary["cost_analysis"]["total_cost_usd"],
            "duration_seconds": wall_clock,
            "num_subtasks": summary["num_subtasks_generated"],
            "iterations": summary["total_iterations"],
            "completed_subtasks": summary["completed_subtasks"],
            "all_complete": summary["final_state"]["all_complete"],
            "execution_log": summary["execution_log"],
            "model": MODEL,
        },
        "metadata": {"max_tokens_per_subtask": 16000, "max_iterations": 8},
    }
    with open(output_dir / "parallel_multi.json", "w") as f:
        json.dump(result, f, indent=2)
    e = result["execution"]
    truncated = sum("stop_reason=max_tokens" in x["notes"] for x in e["execution_log"])
    print(f"   {e['duration_seconds']:.0f}s | {e['total_tokens']:,} tokens | ${e['cost_usd']:.3f} | "
          f"{e['num_subtasks']} subtasks, {e['iterations']} rounds, all complete: {e['all_complete']}, "
          f"cut-off calls: {truncated}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Run experiments on tasks")
    parser.add_argument("--tasks", default="all", help="Comma-separated task IDs or 'all'")
    parser.add_argument("--approaches", default="single,parallel", help="Comma-separated: single,parallel")
    parser.add_argument("--runs", type=int, default=1, help="Independent runs per task")
    parser.add_argument("--max-cost", type=float, default=15.0, help="Stop starting new runs once this many USD are spent")
    parser.add_argument("--overwrite", action="store_true", help="Re-run runs that already have results")
    args = parser.parse_args()

    all_tasks = load_tasks()
    task_ids = list(all_tasks) if args.tasks == "all" else args.tasks.split(",")
    approaches = args.approaches.split(",")
    runners = {"single": ("single_agent.json", run_single_agent),
               "parallel": ("parallel_multi.json", run_parallel_multi_agent)}
    base = Path(__file__).parent.parent / "experiments" / "outputs"

    spent = 0.0
    for run in range(1, args.runs + 1):
        for task_id in task_ids:
            if task_id not in all_tasks:
                print(f"Unknown task {task_id}, skipping")
                continue
            run_dir = base / task_id / f"run_{run}"
            run_dir.mkdir(parents=True, exist_ok=True)
            for approach in approaches:
                if spent >= args.max_cost:
                    print(f"\nCost cap ${args.max_cost:.2f} reached (spent ${spent:.2f}); stopping.")
                    return
                filename, runner = runners[approach]
                if (run_dir / filename).exists() and not args.overwrite:
                    print(f"{task_id} run {run} {approach}: already done (use --overwrite)")
                    continue
                spent += runner(all_tasks[task_id]["description"], task_id, run_dir)["execution"]["cost_usd"]
                print(f"   total spent so far: ${spent:.2f}")

    print(f"\nDone. Spent ${spent:.2f}. Outputs in {base}")


if __name__ == "__main__":
    main()
