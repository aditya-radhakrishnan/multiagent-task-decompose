"""
Stage 1: Run Experiments
Executes tasks with different approaches and saves raw outputs
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
import anthropic

# Add parent directory to path to import auto_orchestrator
sys.path.insert(0, str(Path(__file__).parent))

from auto_orchestrator import AutoDecomposingOrchestrator

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Pricing
INPUT_PRICE_PER_MILLION = 3.0
OUTPUT_PRICE_PER_MILLION = 15.0


def load_tasks():
    """Load task definitions"""
    tasks_file = Path(__file__).parent.parent / "tasks.json"
    with open(tasks_file) as f:
        return json.load(f)["tasks"]


def run_single_agent(task_description: str, task_id: str, output_dir: Path) -> dict:
    """
    Run single agent approach (matches auto_comparison.py exactly)
    """
    print("\n" + "="*60)
    print(f"Running: Single Agent - {task_id}")
    print("="*60)
    
    prompt = f"""You are tasked with completing the following software engineering task:

TASK:
{task_description}

Provide a complete implementation. Focus on core functionality and avoid unnecessary extras like extensive deployment documentation or multiple build tool configurations.
"""
    
    start_time = datetime.now()
    
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=12000,
        thinking={
            "type": "enabled",
            "budget_tokens": 10000
        },
        messages=[{"role": "user", "content": prompt}]
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Extract response
    response = ""
    for block in message.content:
        if hasattr(block, 'text'):
            response += block.text
        elif hasattr(block, 'type') and block.type == 'text':
            response += block.text if hasattr(block, 'text') else ""
    
    if not response and len(message.content) > 0:
        try:
            response = message.content[0].text
        except (AttributeError, IndexError):
            response = str(message.content)
    
    result = {
        "task_id": task_id,
        "approach": "single_agent",
        "timestamp": start_time.isoformat(),
        "execution": {
            "output": response,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
            "cost_usd": (message.usage.input_tokens / 1_000_000 * INPUT_PRICE_PER_MILLION) + 
                       (message.usage.output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MILLION),
            "duration_seconds": duration,
            "model": "claude-sonnet-4-5-20250929"
        },
        "metadata": {
            "max_tokens": 12000,
            "extended_thinking": True,
            "thinking_budget": 10000
        }
    }
    
    # Save output
    output_file = output_dir / "single_agent.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✓ Complete in {duration:.2f}s")
    print(f"  Tokens: {result['execution']['total_tokens']:,} | Cost: ${result['execution']['cost_usd']:.4f}")
    print(f"  Saved to: {output_file}")
    
    return result


def run_parallel_multi_agent(task_description: str, task_id: str, output_dir: Path) -> dict:
    """
    Run parallel multi-agent approach using auto_orchestrator
    """
    print("\n" + "="*60)
    print(f"Running: Parallel Multi-Agent - {task_id}")
    print("="*60)
    
    # Create temporary output directory for orchestrator
    temp_output = output_dir / "parallel_temp"
    
    # Run orchestrator
    t0 = datetime.now()
    orchestrator = AutoDecomposingOrchestrator(output_dir=str(temp_output), clean_start=True)
    orchestrator.run(task_description, max_iterations=8)
    wall_clock = (datetime.now() - t0).total_seconds()
    
    # Load results
    summary_path = temp_output / "debug" / "execution_summary.json"
    with open(summary_path) as f:
        summary = json.load(f)
    
    # Load subtask outputs
    subtask_outputs = {}
    state_dir = temp_output / "state"
    if state_dir.exists():
        for state_file in state_dir.glob("*.md"):
            with open(state_file) as f:
                subtask_outputs[state_file.name] = f.read()
    
    # Load decomposition
    decomp_path = temp_output / "debug" / "task_decomposition.json"
    with open(decomp_path) as f:
        decomposition = json.load(f)
    
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
            "all_complete": summary["final_state"]["all_complete"]
        },
        "metadata": {
            "orchestrator_version": "auto_orchestrator_v2",
            "max_tokens_per_subtask": 16000
        }
    }
    
    # Save output
    output_file = output_dir / "parallel_multi.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✓ Complete")
    print(f"  Subtasks: {result['execution']['num_subtasks']} | Iterations: {result['execution']['iterations']}")
    print(f"  Tokens: {result['execution']['total_tokens']:,} | Cost: ${result['execution']['cost_usd']:.4f}")
    print(f"  Saved to: {output_file}")
    
    return result


def run_best_of_n(task_description: str, task_id: str, output_dir: Path, 
                  target_token_budget: int = None) -> dict:
    """
    Run best-of-N approach
    
    NEW FUNCTIONALITY - Not in original implementation
    
    Args:
        target_token_budget: Total tokens to match (from parallel multi-agent)
                           If None, uses 10x single agent (reasonable default)
    """
    print("\n" + "="*60)
    print(f"Running: Best-of-N - {task_id}")
    print("="*60)
    
    # Calculate N
    tokens_per_attempt = 12000  # Same as single agent max_tokens
    if target_token_budget is None:
        target_token_budget = 120000  # Default: 10 attempts
    
    N = max(1, target_token_budget // tokens_per_attempt)
    print(f"Token budget: {target_token_budget:,}")
    print(f"Tokens per attempt: {tokens_per_attempt:,}")
    print(f"Number of attempts (N): {N}")
    
    prompt = f"""You are tasked with completing the following software engineering task:

TASK:
{task_description}

Provide a complete implementation. Focus on core functionality and avoid unnecessary extras like extensive deployment documentation or multiple build tool configurations.
"""
    
    attempts = []
    total_cost = 0
    
    for i in range(N):
        print(f"\n  Attempt {i+1}/{N}...")
        
        start_time = datetime.now()
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=12000,
            thinking={
                "type": "enabled",
                "budget_tokens": 10000
            },
            messages=[{"role": "user", "content": prompt}]
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Extract response
        response = ""
        for block in message.content:
            if hasattr(block, 'text'):
                response += block.text
        
        cost = (message.usage.input_tokens / 1_000_000 * INPUT_PRICE_PER_MILLION) + \
               (message.usage.output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MILLION)
        
        total_cost += cost
        
        attempt = {
            "attempt_number": i + 1,
            "output": response,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "cost_usd": cost,
            "duration_seconds": duration
        }
        
        attempts.append(attempt)
        print(f"    Tokens: {message.usage.output_tokens:,} | Cost: ${cost:.4f}")
    
    result = {
        "task_id": task_id,
        "approach": "best_of_n",
        "timestamp": datetime.now().isoformat(),
        "execution": {
            "N": N,
            "attempts": attempts,
            "total_tokens": sum(a["input_tokens"] + a["output_tokens"] for a in attempts),
            "cost_usd": total_cost,
            "target_budget": target_token_budget,
            "best_attempt": None  # Will be determined during evaluation
        },
        "metadata": {
            "selection_criteria": "highest_checklist_score",
            "temperature": 1.0,
            "model": "claude-sonnet-4-5-20250929"
        }
    }
    
    # Save output
    output_file = output_dir / "best_of_n.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✓ Complete - {N} attempts")
    print(f"  Total Tokens: {result['execution']['total_tokens']:,} | Total Cost: ${total_cost:.4f}")
    print(f"  Saved to: {output_file}")
    print(f"  Note: Best attempt will be selected during evaluation")
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run experiments on tasks")
    parser.add_argument("--tasks", default="all", help="Comma-separated task IDs or 'all'")
    parser.add_argument("--approaches", default="all", help="Comma-separated: single,parallel,best-of-n or 'all'")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing results")
    
    args = parser.parse_args()
    
    # Load tasks
    all_tasks = load_tasks()
    
    # Select tasks to run
    if args.tasks == "all":
        tasks_to_run = list(all_tasks.keys())
    else:
        tasks_to_run = args.tasks.split(",")
    
    # Select approaches
    if args.approaches == "all":
        approaches = ["single", "parallel", "best-of-n"]
    else:
        approaches = args.approaches.split(",")
    
    print("\n" + "="*60)
    print("EXPERIMENT RUNNER")
    print("="*60)
    print(f"Tasks: {', '.join(tasks_to_run)}")
    print(f"Approaches: {', '.join(approaches)}")
    print(f"Overwrite existing: {args.overwrite}")
    
    # Create base output directory
    base_output = Path(__file__).parent.parent / "experiments" / "outputs"
    base_output.mkdir(parents=True, exist_ok=True)
    
    # Run experiments
    for task_id in tasks_to_run:
        if task_id not in all_tasks:
            print(f"\n⚠️  Unknown task: {task_id}, skipping")
            continue
        
        task = all_tasks[task_id]
        task_output_dir = base_output / task_id
        task_output_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"TASK: {task['name']} ({task_id})")
        print(f"{'='*60}")
        
        # Track parallel token budget for best-of-N matching
        parallel_budget = None
        
        # Run single agent
        if "single" in approaches:
            single_file = task_output_dir / "single_agent.json"
            if single_file.exists() and not args.overwrite:
                print(f"\n✓ Single agent results already exist (use --overwrite to re-run)")
            else:
                run_single_agent(task["description"], task_id, task_output_dir)
        
        # Run parallel multi-agent
        if "parallel" in approaches:
            parallel_file = task_output_dir / "parallel_multi.json"
            if parallel_file.exists() and not args.overwrite:
                print(f"\n✓ Parallel multi-agent results already exist (use --overwrite to re-run)")
                # Load to get token budget
                with open(parallel_file) as f:
                    parallel_budget = json.load(f)["execution"]["total_tokens"]
            else:
                result = run_parallel_multi_agent(task["description"], task_id, task_output_dir)
                parallel_budget = result["execution"]["total_tokens"]
        
        # Run best-of-N
        if "best-of-n" in approaches:
            best_file = task_output_dir / "best_of_n.json"
            if best_file.exists() and not args.overwrite:
                print(f"\n✓ Best-of-N results already exist (use --overwrite to re-run)")
            else:
                # If we ran or loaded parallel, match its budget
                if parallel_budget is None and Path(task_output_dir / "parallel_multi.json").exists():
                    with open(task_output_dir / "parallel_multi.json") as f:
                        parallel_budget = json.load(f)["execution"]["total_tokens"]
                
                run_best_of_n(task["description"], task_id, task_output_dir, parallel_budget)
    
    print("\n" + "="*60)
    print("EXPERIMENTS COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {base_output}")
    print("\nNext steps:")
    print("  1. Evaluate: python src/evaluate_experiments.py")
    print("  2. Visualize: python src/visualize_experiments.py")


if __name__ == "__main__":
    main()
