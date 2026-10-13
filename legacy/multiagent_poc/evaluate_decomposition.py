import os
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class DecompositionEvaluator:
    """
    Evaluates the quality of automatic task decomposition and execution
    """
    
    def __init__(self, output_dir: str = "./auto_poc_output"):
        self.output_dir = output_dir
        self.debug_dir = os.path.join(output_dir, "debug")
        self.state_dir = os.path.join(output_dir, "state")
        
        self.eval_input_tokens = 0
        self.eval_output_tokens = 0
        self.input_price_per_million = 3.0
        self.output_price_per_million = 15.0
    
    def load_artifacts(self) -> dict:
        """Load all relevant artifacts from the auto-decomposition run"""
        artifacts = {
            "task_decomposition": None,
            "execution_summary": None,
            "state_files": {}
        }
        
        # Load task decomposition
        decomp_path = os.path.join(self.debug_dir, "task_decomposition.json")
        if os.path.exists(decomp_path):
            with open(decomp_path, 'r') as f:
                artifacts["task_decomposition"] = json.load(f)
        
        # Load execution summary
        summary_path = os.path.join(self.debug_dir, "execution_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                artifacts["execution_summary"] = json.load(f)
        
        # Load state files
        if os.path.exists(self.state_dir):
            for filename in os.listdir(self.state_dir):
                if filename.endswith('.md'):
                    with open(os.path.join(self.state_dir, filename), 'r') as f:
                        artifacts["state_files"][filename] = f.read()
        
        return artifacts
    
    def build_evaluation_prompt(self, artifacts: dict) -> str:
        """Build evaluation prompt for decomposition quality"""
        
        decomposition = artifacts.get("task_decomposition", {})
        summary = artifacts.get("execution_summary", {})
        state_files = artifacts.get("state_files", {})
        
        main_task = summary.get("main_task", "Unknown")
        reasoning = decomposition.get("reasoning", "No reasoning provided")
        subtasks = decomposition.get("subtasks", [])
        
        # Format subtasks for readability
        subtasks_formatted = ""
        for st in subtasks:
            deps = st.get('depends_on', [])
            dep_str = f" → Depends on: {', '.join(deps)}" if deps else " → No dependencies"
            subtasks_formatted += f"- [{st['id']}] {st['name']}{dep_str}\n"
            subtasks_formatted += f"  Description: {st['description']}\n"
            subtasks_formatted += f"  Complexity: {st.get('estimated_complexity', 'unknown')}\n\n"
        
        # Execution results
        completed = summary.get("completed_subtasks", [])
        iterations = summary.get("total_iterations", 0)
        all_complete = summary.get("final_state", {}).get("all_complete", False)
        
        # Sample state files (first 1000 chars each)
        state_samples = ""
        for filename, content in list(state_files.items())[:3]:
            state_samples += f"## {filename}\n```\n{content[:1000]}...\n```\n\n"
        
        prompt = f"""You are evaluating an automatic task decomposition system for multi-agent coordination.

# THE EXPERIMENT

The system was given a task and automatically:
1. Decomposed it into subtasks
2. Identified dependencies
3. Spawned agents to execute each subtask
4. Coordinated their work through state files

# ORIGINAL TASK

{main_task}

# DECOMPOSITION OUTPUT

**Reasoning:**
{reasoning}

**Generated Subtasks ({len(subtasks)}):**
{subtasks_formatted}

# EXECUTION RESULTS

- **Iterations:** {iterations}
- **Completed:** {len(completed)}/{len(subtasks)} subtasks
- **All Complete:** {all_complete}
- **Completed IDs:** {', '.join(completed) if completed else 'None'}

# SAMPLE OUTPUTS

{state_samples}

---

# YOUR EVALUATION

Analyze this automatic decomposition and provide:

## 1. Decomposition Quality (Score: 1-10)

**Criteria:**
- **Granularity**: Are subtasks appropriately sized? (not too fine-grained, not too coarse)
- **Clarity**: Are descriptions clear and actionable?
- **Completeness**: Does the decomposition cover the full task?
- **Logical structure**: Does the breakdown make engineering sense?

**Questions to answer:**
- How many subtasks were generated and is that appropriate?
- Are the subtasks independently achievable?
- Would a human engineer decompose this task similarly?

## 2. Dependency Identification (Score: 1-10)

**Criteria:**
- **Correctness**: Are dependencies accurately identified?
- **Completeness**: Are all dependencies captured?
- **Not over-constrained**: Are there unnecessary dependencies?

**Questions to answer:**
- Can the dependency graph actually be executed (no circular deps)?
- Do the dependencies make logical sense?
- Could any subtasks be parallelized that aren't?

## 3. Execution Success (Score: 1-10)

**Criteria:**
- **Completion rate**: Did all subtasks finish?
- **Coordination**: Did agents properly wait for dependencies?
- **Output quality**: Did agents produce what was expected?

**Questions to answer:**
- Did the execution match the decomposition plan?
- Were there coordination failures?
- Did agents interpret their subtasks correctly?

## 4. Efficiency Analysis

**Questions to answer:**
- Could this have been done with fewer subtasks?
- Were there wasted iterations?
- Was the decomposition too complex or too simple?

## 5. Comparison to Optimal Decomposition

**Provide:**
- Your assessment of the optimal way to decompose this task
- How the actual decomposition compares
- Specific improvements that could be made

## 6. Key Insights

What did you learn about automatic decomposition from this run?
- What worked well?
- What failed or was suboptimal?
- Patterns to encourage or avoid?

## 7. Overall Assessment

- **Overall Score**: X/30 (sum of three 1-10 scores)
- **Grade**: Excellent / Good / Fair / Poor
- **Verdict**: Did automatic decomposition work better than manual decomposition would have?

Be specific and reference actual evidence from the decomposition and execution logs.
"""
        
        return prompt
    
    def evaluate(self) -> str:
        """Run evaluation"""
        print("\n" + "="*60)
        print("EVALUATING TASK DECOMPOSITION")
        print("="*60)
        
        artifacts = self.load_artifacts()
        
        if not artifacts["task_decomposition"]:
            print("Error: No task decomposition found. Run auto_orchestrator.py first.")
            return None
        
        print("\nBuilding evaluation prompt...")
        prompt = self.build_evaluation_prompt(artifacts)
        
        print("Calling AI evaluator...\n")
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        self.eval_input_tokens = message.usage.input_tokens
        self.eval_output_tokens = message.usage.output_tokens
        
        evaluation = message.content[0].text
        
        # Calculate costs
        eval_input_cost = (self.eval_input_tokens / 1_000_000) * self.input_price_per_million
        eval_output_cost = (self.eval_output_tokens / 1_000_000) * self.output_price_per_million
        eval_total_cost = eval_input_cost + eval_output_cost
        
        # Load orchestrator costs
        orchestrator_cost = 0.0
        if artifacts["execution_summary"] and "cost_analysis" in artifacts["execution_summary"]:
            orchestrator_cost = artifacts["execution_summary"]["cost_analysis"].get("total_cost_usd", 0.0)
        
        # Save evaluation
        eval_path = os.path.join(self.debug_dir, "decomposition_evaluation.md")
        with open(eval_path, 'w') as f:
            f.write("# Task Decomposition Evaluation\n\n")
            f.write(evaluation)
            f.write("\n\n---\n\n")
            f.write("## Cost Analysis\n\n")
            f.write(f"- **Evaluation Input Tokens:** {self.eval_input_tokens:,}\n")
            f.write(f"- **Evaluation Output Tokens:** {self.eval_output_tokens:,}\n")
            f.write(f"- **Evaluation Cost:** ${eval_total_cost:.4f}\n")
            if orchestrator_cost > 0:
                total_experiment_cost = orchestrator_cost + eval_total_cost
                f.write(f"\n### Total Experiment Cost\n")
                f.write(f"- **Auto-Orchestrator Cost:** ${orchestrator_cost:.4f}\n")
                f.write(f"- **Evaluation Cost:** ${eval_total_cost:.4f}\n")
                f.write(f"- **Total Cost:** ${total_experiment_cost:.4f}\n")
        
        print("="*60)
        print("EVALUATION RESULTS")
        print("="*60)
        print(evaluation)
        print("\n" + "="*60)
        print("COST SUMMARY")
        print("="*60)
        print(f"Evaluation Cost: ${eval_total_cost:.4f}")
        if orchestrator_cost > 0:
            print(f"Orchestrator Cost: ${orchestrator_cost:.4f}")
            print(f"Total Cost: ${orchestrator_cost + eval_total_cost:.4f}")
        print("="*60)
        print(f"\nEvaluation saved to: {eval_path}")
        print("="*60)
        
        return evaluation


if __name__ == "__main__":
    evaluator = DecompositionEvaluator()
    evaluator.evaluate()
