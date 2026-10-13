"""
Run batch experiments for statistical validation
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import anthropic
from task_generator import get_all_tasks

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


class BatchExperimentRunner:
    """Run multiple experiments and collect results for statistical analysis"""
    
    def __init__(self, output_dir: str = "./batch_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.results = []
        self.input_price_per_million = 3.0
        self.output_price_per_million = 15.0
    
    def run_single_agent(self, task_id: str, task_description: str) -> Dict:
        """Run single agent approach with extended thinking"""
        print(f"  Running single agent (with extended thinking) for {task_id}...")
        
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
        
        response = message.content[0].text
        
        # Track thinking tokens separately
        thinking_tokens = 0
        for block in message.content:
            if hasattr(block, 'type') and block.type == 'thinking':
                thinking_tokens += len(block.thinking.split())  # Rough estimate
        
        # Calculate cost (thinking tokens priced differently)
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        
        cost = (input_tokens / 1_000_000 * self.input_price_per_million) + \
               (output_tokens / 1_000_000 * self.output_price_per_million)
        
        # Save output
        output_path = os.path.join(self.output_dir, f"{task_id}_single_agent.md")
        with open(output_path, 'w') as f:
            f.write(response)
        
        return {
            "approach": "single_agent",
            "task_id": task_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost,
            "duration_seconds": duration,
            "output_file": output_path,
            "timestamp": start_time.isoformat(),
            "extended_thinking": True
        }
    
    def evaluate_output(self, task_id: str, task_description: str, 
                       single_agent_result: Dict, auto_decomp_result: Dict) -> Dict:
        """Use AI to evaluate and compare both outputs"""
        print(f"  Evaluating outputs for {task_id}...")
        
        # Load outputs
        with open(single_agent_result["output_file"], 'r') as f:
            single_output = f.read()[:5000]  # Truncate for evaluation
        
        # For auto-decomp, load state files
        auto_output = ""
        state_dir = os.path.join(self.output_dir, f"{task_id}_auto_decomp_state")
        if os.path.exists(state_dir):
            for filename in os.listdir(state_dir):
                if filename.endswith('.md'):
                    with open(os.path.join(state_dir, filename), 'r') as f:
                        auto_output += f"## {filename}\n{f.read()[:2000]}\n\n"
        
        eval_prompt = f"""Evaluate these two implementations of the same task.

TASK: {task_description}

# SINGLE AGENT OUTPUT
{single_output}

# AUTO-DECOMPOSITION OUTPUT  
{auto_output}

Provide scores (1-10) for each approach:

1. **Completeness**: Are all required components present?
2. **Correctness**: Does the implementation work correctly?
3. **Code Quality**: Is the code well-structured and maintainable?

Also assess:
- Which approach produced better output overall?
- Estimate completion percentage for each (0-100%)

Respond in JSON format:
{{
  "single_agent": {{
    "completeness": X,
    "correctness": X, 
    "code_quality": X,
    "total": X,
    "completion_pct": X
  }},
  "auto_decomposition": {{
    "completeness": X,
    "correctness": X,
    "code_quality": X, 
    "total": X,
    "completion_pct": X
  }},
  "winner": "single_agent" or "auto_decomposition",
  "notes": "brief explanation"
}}
"""
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": eval_prompt}]
        )
        
        # Parse JSON response
        import re
        response = message.content[0].text
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            evaluation = json.loads(json_match.group())
        else:
            # Fallback if parsing fails
            evaluation = {
                "single_agent": {"completeness": 5, "correctness": 5, "code_quality": 5, "total": 15, "completion_pct": 50},
                "auto_decomposition": {"completeness": 5, "correctness": 5, "code_quality": 5, "total": 15, "completion_pct": 50},
                "winner": "tie",
                "notes": "Evaluation parsing failed"
            }
        
        # Track evaluation cost
        eval_cost = (message.usage.input_tokens / 1_000_000 * self.input_price_per_million) + \
                   (message.usage.output_tokens / 1_000_000 * self.output_price_per_million)
        
        evaluation["evaluation_cost_usd"] = eval_cost
        
        return evaluation
    
    def run_experiment(self, task_id: str, task_name: str, task_description: str, 
                       complexity: str) -> Dict:
        """Run complete experiment: both approaches + evaluation"""
        print(f"\n{'='*60}")
        print(f"Experiment: {task_id} - {task_name}")
        print(f"Complexity: {complexity}")
        print(f"{'='*60}")
        
        # Run single agent
        single_result = self.run_single_agent(task_id, task_description)
        
        # Run auto-decomposition (using existing auto_orchestrator)
        print(f"  Running auto-decomposition for {task_id}...")
        
        # Import here to avoid circular dependency
        from auto_orchestrator import AutoDecomposingOrchestrator
        
        auto_output_dir = os.path.join(self.output_dir, f"{task_id}_auto_decomp")
        orchestrator = AutoDecomposingOrchestrator(output_dir=auto_output_dir, clean_start=True)
        orchestrator.run(task_description, max_iterations=8)
        
        # Load auto-decomp results
        summary_path = os.path.join(auto_output_dir, "debug", "execution_summary.json")
        with open(summary_path, 'r') as f:
            auto_summary = json.load(f)
        
        auto_result = {
            "approach": "auto_decomposition",
            "task_id": task_id,
            "input_tokens": auto_summary["cost_analysis"]["total_input_tokens"],
            "output_tokens": auto_summary["cost_analysis"]["total_output_tokens"],
            "total_tokens": auto_summary["cost_analysis"]["total_tokens"],
            "cost_usd": auto_summary["cost_analysis"]["total_cost_usd"],
            "num_subtasks": auto_summary["num_subtasks_generated"],
            "iterations": auto_summary["total_iterations"],
            "all_complete": auto_summary["final_state"]["all_complete"],
            "output_dir": auto_output_dir
        }
        
        # Evaluate both
        evaluation = self.evaluate_output(task_id, task_description, single_result, auto_result)
        
        # Combine results
        experiment_result = {
            "task_id": task_id,
            "task_name": task_name,
            "complexity": complexity,
            "timestamp": datetime.now().isoformat(),
            "single_agent": single_result,
            "auto_decomposition": auto_result,
            "evaluation": evaluation
        }
        
        self.results.append(experiment_result)
        
        # Save incremental results
        self.save_results()
        
        print(f"  ✓ Experiment complete")
        print(f"    Single agent: ${single_result['cost_usd']:.4f}, "
              f"{evaluation['single_agent']['total']}/30 quality")
        print(f"    Auto-decomp: ${auto_result['cost_usd']:.4f}, "
              f"{evaluation['auto_decomposition']['total']}/30 quality")
        print(f"    Winner: {evaluation['winner']}")
        
        return experiment_result
    
    def save_results(self):
        """Save all results to JSON"""
        results_path = os.path.join(self.output_dir, "batch_results.json")
        with open(results_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_experiments": len(self.results),
                "results": self.results
            }, f, indent=2)
    
    def run_batch(self, n_per_complexity: int = 5):
        """Run full batch of experiments"""
        tasks = get_all_tasks(n_per_complexity)
        
        total_experiments = sum(len(tasks[c]) for c in tasks)
        print(f"\n{'='*60}")
        print(f"BATCH EXPERIMENT RUN")
        print(f"{'='*60}")
        print(f"Total experiments: {total_experiments}")
        print(f"Per complexity: {n_per_complexity}")
        print(f"Estimated cost: ${total_experiments * 0.35:.2f} - ${total_experiments * 0.50:.2f}")
        print(f"Estimated time: {total_experiments * 3:.0f} - {total_experiments * 5:.0f} minutes")
        print(f"{'='*60}\n")
        
        input("Press Enter to start batch run...")
        
        experiment_num = 0
        for complexity in ["simple", "medium", "complex"]:
            for task in tasks[complexity]:
                experiment_num += 1
                print(f"\n[{experiment_num}/{total_experiments}]")
                
                self.run_experiment(
                    task["id"],
                    task["name"],
                    task["description"],
                    complexity
                )
        
        print(f"\n{'='*60}")
        print("BATCH RUN COMPLETE")
        print(f"{'='*60}")
        print(f"Total experiments: {len(self.results)}")
        print(f"Results saved to: {self.output_dir}/batch_results.json")
        print(f"Run statistical analysis: python analyze_results.py")


if __name__ == "__main__":
    import sys
    
    n = 5  # Default
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    
    runner = BatchExperimentRunner()
    runner.run_batch(n_per_complexity=n)
