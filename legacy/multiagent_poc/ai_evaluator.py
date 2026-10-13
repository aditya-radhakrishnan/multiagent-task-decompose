import os
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class AIEvaluator:
    def __init__(self, output_dir: str = "./poc_output"):
        self.output_dir = output_dir
        self.debug_dir = os.path.join(output_dir, "debug")
        self.state_dir = os.path.join(output_dir, "state")
        
        # Cost tracking for evaluator
        self.eval_input_tokens = 0
        self.eval_output_tokens = 0
        self.input_price_per_million = 3.0
        self.output_price_per_million = 15.0
    
    def gather_all_artifacts(self) -> dict:
        """Collect all relevant files for evaluation"""
        artifacts = {
            "execution_summary": None,
            "execution_log": None,
            "state_files": {},
            "sample_prompts": {},
            "sample_responses": {}
        }
        
        # Load execution summary markdown
        summary_md = os.path.join(self.debug_dir, "execution_summary.md")
        if os.path.exists(summary_md):
            with open(summary_md, 'r') as f:
                artifacts["execution_summary"] = f.read()
        
        # Load execution log JSON
        summary_json = os.path.join(self.debug_dir, "execution_summary.json")
        if os.path.exists(summary_json):
            with open(summary_json, 'r') as f:
                artifacts["execution_log"] = json.load(f)
        
        # Load all state files
        if os.path.exists(self.state_dir):
            for filename in os.listdir(self.state_dir):
                if filename.endswith('.md'):
                    filepath = os.path.join(self.state_dir, filename)
                    with open(filepath, 'r') as f:
                        artifacts["state_files"][filename] = f.read()
        
        # Load sample prompts and responses (first and last iteration for each agent)
        if os.path.exists(self.debug_dir):
            for subtask_id in ['A', 'B', 'C']:
                # First iteration
                prompt_file = f"subtask_{subtask_id}_iter_0_prompt.txt"
                response_file = f"subtask_{subtask_id}_iter_0_response.txt"
                
                prompt_path = os.path.join(self.debug_dir, prompt_file)
                response_path = os.path.join(self.debug_dir, response_file)
                
                if os.path.exists(prompt_path):
                    with open(prompt_path, 'r') as f:
                        artifacts["sample_prompts"][f"{subtask_id}_first"] = f.read()
                
                if os.path.exists(response_path):
                    with open(response_path, 'r') as f:
                        artifacts["sample_responses"][f"{subtask_id}_first"] = f.read()
                
                # Try to find last iteration (check iterations 0-9)
                for i in range(9, -1, -1):
                    last_prompt = os.path.join(self.debug_dir, f"subtask_{subtask_id}_iter_{i}_prompt.txt")
                    last_response = os.path.join(self.debug_dir, f"subtask_{subtask_id}_iter_{i}_response.txt")
                    
                    if os.path.exists(last_response):
                        with open(last_response, 'r') as f:
                            artifacts["sample_responses"][f"{subtask_id}_last"] = f.read()
                        break
        
        return artifacts
    
    def build_evaluation_prompt(self, artifacts: dict) -> str:
        """Build a comprehensive evaluation prompt"""
        
        prompt = """You are evaluating an experiment in multi-agent coordination. The goal was to test whether AI agents can coordinate autonomously through shared state files.

# EXPERIMENT SETUP

Three AI agents worked on creating a new API feature:
- **Agent A**: Design the API contract (no dependencies)
- **Agent B**: Implement the backend (depends on A's contract)
- **Agent C**: Implement the frontend API caller (depends on A's contract)

Each agent:
1. Reads all state files before each step (to see what others have done)
2. Decides if it can proceed or if it's blocked
3. Writes its full output to its own state file
4. Declares itself BLOCKED or COMPLETE as appropriate

The key question: **Can agents coordinate purely through reading each other's state files, without explicit orchestration?**

# EXECUTION TIMELINE

"""
        
        if artifacts["execution_summary"]:
            prompt += artifacts["execution_summary"] + "\n\n"
        
        prompt += "# FINAL STATE FILES\n\n"
        
        for filename, content in artifacts["state_files"].items():
            prompt += f"## {filename}\n\n```\n{content}\n```\n\n"
        
        prompt += """# SAMPLE AGENT INTERACTIONS

Here are some sample prompts and responses to understand agent behavior:

"""
        
        # Add a few sample interactions
        for key in ["A_first", "B_first", "C_first"]:
            if key in artifacts["sample_responses"]:
                prompt += f"## Agent {key[0]} - First Iteration Response (excerpt)\n\n"
                # Truncate to first 1000 chars to save tokens
                prompt += f"```\n{artifacts['sample_responses'][key][:1500]}...\n```\n\n"
        
        prompt += """# YOUR TASK

Analyze this experiment and provide:

1. **Overall Assessment**: Did the coordination work? Rate: SUCCESS / PARTIAL SUCCESS / FAILURE

2. **Key Observations**: What happened? Focus on:
   - Did agents respect dependencies (did B/C wait for A)?
   - Did agents unblock themselves when ready?
   - Did agents produce compatible outputs?
   - Any unexpected behaviors (good or bad)?

3. **Interesting Insights**: What did you notice that might not be obvious? Examples:
   - Coordination patterns that emerged
   - How agents interpreted ambiguous situations
   - Quality of the actual code/artifacts produced
   - Efficiency of coordination (wasted iterations?)

4. **Problems & Failure Modes**: What went wrong or could go wrong?
   - Did agents hallucinate information?
   - Did they get confused by state files?
   - Any coordination breakdowns?

5. **Recommendations**: How could this be improved?
   - Prompt engineering suggestions
   - State file format changes
   - Additional mechanisms needed?

Be specific and reference actual evidence from the logs. Focus on insights that would help iterate on the design.
"""
        
        return prompt
    
    def evaluate(self) -> str:
        """Run AI evaluation"""
        print("Gathering execution artifacts...")
        artifacts = self.gather_all_artifacts()
        
        if not artifacts["execution_summary"]:
            print("Error: No execution summary found. Run the orchestrator first.")
            return None
        
        # Load orchestrator costs if available
        orchestrator_cost = None
        if artifacts["execution_log"] and "cost_analysis" in artifacts["execution_log"]:
            orchestrator_cost = artifacts["execution_log"]["cost_analysis"]
        
        print("Building evaluation prompt...")
        prompt = self.build_evaluation_prompt(artifacts)
        
        print("Calling AI evaluator (this may take a moment)...")
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Track evaluator token usage
        self.eval_input_tokens = message.usage.input_tokens
        self.eval_output_tokens = message.usage.output_tokens
        
        evaluation = message.content[0].text
        
        # Calculate costs
        eval_input_cost = (self.eval_input_tokens / 1_000_000) * self.input_price_per_million
        eval_output_cost = (self.eval_output_tokens / 1_000_000) * self.output_price_per_million
        eval_total_cost = eval_input_cost + eval_output_cost
        
        # Save evaluation
        eval_path = os.path.join(self.debug_dir, "ai_evaluation.md")
        with open(eval_path, 'w') as f:
            f.write("# AI Evaluation of Agent Coordination PoC\n\n")
            f.write(evaluation)
            f.write("\n\n---\n\n")
            f.write("## Evaluation Cost Analysis\n\n")
            f.write(f"- **Evaluation Input Tokens:** {self.eval_input_tokens:,}\n")
            f.write(f"- **Evaluation Output Tokens:** {self.eval_output_tokens:,}\n")
            f.write(f"- **Evaluation Cost:** ${eval_total_cost:.4f}\n")
            if orchestrator_cost:
                total_experiment_cost = orchestrator_cost['total_cost_usd'] + eval_total_cost
                f.write(f"\n### Total Experiment Cost\n")
                f.write(f"- **Orchestrator Cost:** ${orchestrator_cost['total_cost_usd']:.4f}\n")
                f.write(f"- **Evaluation Cost:** ${eval_total_cost:.4f}\n")
                f.write(f"- **Total Cost:** ${total_experiment_cost:.4f}\n")
        
        print(f"\n{'='*60}")
        print("AI EVALUATION")
        print(f"{'='*60}\n")
        print(evaluation)
        print(f"\n{'='*60}")
        print("EVALUATION COST")
        print(f"{'='*60}")
        print(f"Input Tokens:  {self.eval_input_tokens:,}")
        print(f"Output Tokens: {self.eval_output_tokens:,}")
        print(f"Total Cost:    ${eval_total_cost:.4f}")
        if orchestrator_cost:
            total_experiment_cost = orchestrator_cost['total_cost_usd'] + eval_total_cost
            print(f"\nTotal Experiment Cost (Orchestrator + Evaluation):")
            print(f"  ${total_experiment_cost:.4f}")
        print(f"{'='*60}")
        print(f"Evaluation saved to: {eval_path}")
        print(f"{'='*60}")
        
        return evaluation


if __name__ == "__main__":
    evaluator = AIEvaluator()
    evaluator.evaluate()
