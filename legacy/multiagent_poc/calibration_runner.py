"""
Calibration Runner - Measures actual performance of single-agent execution
Integrates with existing task_generator.py and meta_prompt_tester.py
"""

import json
import time
from pathlib import Path
from anthropic import Anthropic
import os
from task_generator import SIMPLE_TASKS, MEDIUM_TASKS, COMPLEX_TASKS

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Map task IDs to ground truth from meta_prompt_tester.py
GROUND_TRUTH = {
    "simple_1": "SINGLE_AGENT",  # Todo API
    "simple_2": "SINGLE_AGENT",  # Weather dashboard
    "medium_1": "SINGLE_AGENT",  # Auth system (after extended thinking)
    "medium_2": "DECOMPOSE",     # Payment integration
    "complex_1": "SINGLE_AGENT", # E-commerce (tightly coupled)
    "complex_3": "DECOMPOSE",    # Analytics
}


def get_task_by_id(task_id: str) -> dict:
    """Get task definition from task_generator"""
    all_tasks = SIMPLE_TASKS + MEDIUM_TASKS + COMPLEX_TASKS
    for task in all_tasks:
        if task["id"] == task_id:
            return task
    return None


def run_single_agent_with_extended_thinking(task_id: str, task_info: dict, client: Anthropic) -> dict:
    """Run single agent with extended thinking (matching your batch_runner approach)"""
    
    print(f"\n{'='*60}")
    print(f"Running: {task_info['name']} ({task_id})")
    print(f"{'='*60}")
    print(f"DEBUG: Task description length: {len(task_info['description'])} chars")
    print(f"DEBUG: Using model: claude-sonnet-4-5-20250929")
    print(f"DEBUG: Max tokens: 12000, Thinking budget: 10000")
    
    # Use EXACT same prompt as auto_comparison.py for consistency
    prompt = f"""You are tasked with completing the following software engineering task:

TASK:
{task_info['description']}

Provide a complete implementation. Focus on core functionality and avoid unnecessary extras like extensive deployment documentation or multiple build tool configurations.
"""
    
    start_time = time.time()
    
    try:
        # Match auto_comparison.py exactly: max_tokens=12000, thinking budget=10000
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",  # Use same model as comparisons
            max_tokens=12000,  # Match auto_comparison.py
            thinking={
                "type": "enabled",
                "budget_tokens": 10000
            },
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        execution_time = time.time() - start_time
        
        # Extract response text
        response_text = ""
        thinking_content = ""
        for block in response.content:
            if hasattr(block, 'type'):
                if block.type == 'text' and hasattr(block, 'text'):
                    response_text += block.text
                elif block.type == 'thinking' and hasattr(block, 'thinking'):
                    thinking_content += block.thinking
        
        # Measure tokens
        actual_input_tokens = response.usage.input_tokens
        actual_output_tokens = response.usage.output_tokens
        
        # Check if truncated
        truncated = response.stop_reason == "max_tokens"
        
        # Calculate cost (Claude Sonnet 4.5 pricing)
        input_price_per_million = 3.0
        output_price_per_million = 15.0
        cost = (actual_input_tokens / 1_000_000 * input_price_per_million) + \
               (actual_output_tokens / 1_000_000 * output_price_per_million)
        
        result = {
            "task_id": task_id,
            "task_name": task_info['name'],
            "ground_truth": GROUND_TRUTH.get(task_id, "UNKNOWN"),
            "actual_input_tokens": actual_input_tokens,
            "actual_output_tokens": actual_output_tokens,
            "truncated": truncated,
            "stop_reason": response.stop_reason,
            "execution_time_seconds": round(execution_time, 2),
            "response_length_chars": len(response_text),
            "thinking_length_chars": len(thinking_content),
            "cost_usd": cost,
            "success": not truncated,
            "model": response.model,
            "extended_thinking_enabled": True
        }
        
        # Validate against ground truth
        if GROUND_TRUTH.get(task_id) == "SINGLE_AGENT" and truncated:
            result["ground_truth_validation"] = "FAILED - Expected SINGLE_AGENT to work, but truncated"
        elif GROUND_TRUTH.get(task_id) == "DECOMPOSE" and not truncated:
            result["ground_truth_validation"] = "QUESTIONABLE - Expected DECOMPOSE, but single agent completed"
        elif GROUND_TRUTH.get(task_id) == "SINGLE_AGENT" and not truncated:
            result["ground_truth_validation"] = "CONFIRMED - SINGLE_AGENT worked as expected"
        else:
            result["ground_truth_validation"] = "EXPECTED - Task marked for DECOMPOSE"
        
        # Save output
        output_dir = Path("calibration_output") / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / "response.txt", "w") as f:
            f.write(response_text)
        
        if thinking_content:
            with open(output_dir / "thinking.txt", "w") as f:
                f.write(thinking_content)
        
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Print summary
        status = "✓" if not truncated else "⚠️  TRUNCATED"
        print(f"{status} Completed in {execution_time:.1f}s")
        print(f"  Output tokens: {actual_output_tokens:,}")
        print(f"  Ground truth: {result['ground_truth']}")
        print(f"  Validation: {result['ground_truth_validation']}")
        
        return result
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return {
            "task_id": task_id,
            "task_name": task_info['name'],
            "error": str(e),
            "success": False
        }


def run_calibration(task_ids: list = None):
    """Run calibration on specified tasks"""
    
    client_instance = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    # Default to the 6 tasks from ground truth
    if task_ids is None:
        task_ids = list(GROUND_TRUTH.keys())
    
    results = []
    
    print(f"\n🎯 Starting calibration run for {len(task_ids)} tasks")
    print(f"Tasks: {', '.join(task_ids)}\n")
    print("This will validate the ground truth by running single agents with extended thinking")
    print(f"Estimated cost: ${len(task_ids) * 0.40:.2f} - ${len(task_ids) * 0.60:.2f}\n")
    
    for task_id in task_ids:
        task_info = get_task_by_id(task_id)
        
        if not task_info:
            print(f"⚠️  Unknown task: {task_id}, skipping")
            continue
        
        result = run_single_agent_with_extended_thinking(task_id, task_info, client_instance)
        results.append(result)
        
        # Save incremental results
        with open("calibration_output/results.json", "w") as f:
            json.dump(results, f, indent=2)
    
    # Generate summary report
    generate_summary_report(results)
    
    return results


def generate_summary_report(results: list):
    """Generate markdown summary of calibration results"""
    
    report = ["# Calibration Results - Ground Truth Validation\n\n"]
    report.append("## Purpose\n")
    report.append("This calibration validates the ground truth labels by running single agents ")
    report.append("with extended thinking on each task. Tasks marked SINGLE_AGENT should complete ")
    report.append("without truncation. Tasks marked DECOMPOSE may truncate or be very large.\n\n")
    
    report.append("## Summary\n\n")
    report.append("| Task | Ground Truth | Output Tokens | Truncated | Validation |\n")
    report.append("|------|--------------|---------------|-----------|------------|\n")
    
    for r in results:
        if not r.get('success'):
            continue
        
        truncated_mark = "Yes ⚠️" if r['truncated'] else "No ✓"
        validation = r.get('ground_truth_validation', 'N/A')
        
        # Shorten validation for table
        if "CONFIRMED" in validation:
            val_short = "✓ Confirmed"
        elif "FAILED" in validation:
            val_short = "❌ Failed"
        elif "QUESTIONABLE" in validation:
            val_short = "⚠️  Questionable"
        else:
            val_short = "Expected"
        
        report.append(
            f"| {r['task_name']} | {r['ground_truth']} | "
            f"{r['actual_output_tokens']:,} | {truncated_mark} | {val_short} |\n"
        )
    
    report.append("\n## Detailed Analysis\n\n")
    
    # Group by validation status
    confirmed = [r for r in results if 'CONFIRMED' in r.get('ground_truth_validation', '')]
    failed = [r for r in results if 'FAILED' in r.get('ground_truth_validation', '')]
    questionable = [r for r in results if 'QUESTIONABLE' in r.get('ground_truth_validation', '')]
    
    if confirmed:
        report.append(f"### ✓ Confirmed Ground Truth ({len(confirmed)})\n\n")
        for r in confirmed:
            report.append(f"**{r['task_name']}** ({r['task_id']})\n")
            report.append(f"- Ground truth: {r['ground_truth']}\n")
            report.append(f"- Output tokens: {r['actual_output_tokens']:,}\n")
            report.append(f"- {r['ground_truth_validation']}\n\n")
    
    if questionable:
        report.append(f"### ⚠️  Questionable Ground Truth ({len(questionable)})\n\n")
        for r in questionable:
            report.append(f"**{r['task_name']}** ({r['task_id']})\n")
            report.append(f"- Ground truth: {r['ground_truth']}\n")
            report.append(f"- Output tokens: {r['actual_output_tokens']:,}\n")
            report.append(f"- {r['ground_truth_validation']}\n")
            report.append(f"- **Action**: Consider re-evaluating if this task needs DECOMPOSE\n\n")
    
    if failed:
        report.append(f"### ❌ Failed Ground Truth ({len(failed)})\n\n")
        for r in failed:
            report.append(f"**{r['task_name']}** ({r['task_id']})\n")
            report.append(f"- Ground truth: {r['ground_truth']}\n")
            report.append(f"- Output tokens: {r['actual_output_tokens']:,}\n")
            report.append(f"- {r['ground_truth_validation']}\n")
            report.append(f"- **Action**: Ground truth should be changed to DECOMPOSE\n\n")
    
    # Cost summary
    report.append("## Cost Summary\n\n")
    total_cost = sum(r.get('cost_usd', 0) for r in results if r.get('success'))
    report.append(f"Total calibration cost: ${total_cost:.4f}\n\n")
    
    # Save report
    with open("calibration_output/calibration_report.md", "w") as f:
        f.writelines(report)
    
    print("\n✅ Calibration complete!")
    print("📊 Report saved to: calibration_output/calibration_report.md")
    print(f"\n📈 Results Summary:")
    print(f"  ✓ Confirmed: {len(confirmed)}")
    print(f"  ⚠️  Questionable: {len(questionable)}")
    print(f"  ❌ Failed: {len(failed)}")
    
    if questionable or failed:
        print(f"\n⚠️  Ground truth issues detected! Review the report.")


if __name__ == "__main__":
    import sys
    
    # Usage: python calibration_runner.py [task_ids...]
    # Or: python calibration_runner.py (runs all ground truth tasks)
    
    task_ids = sys.argv[1:] if len(sys.argv) > 1 else None
    run_calibration(task_ids)
