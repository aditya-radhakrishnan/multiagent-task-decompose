import os
import json
from datetime import datetime
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class CoordinationComparison:
    """
    Compare different coordination approaches:
    1. Multi-agent with state file coordination (current approach)
    2. Single agent doing all tasks
    3. Independent agents (no coordination)
    """
    
    def __init__(self, output_dir: str = "./comparison_output", clean_start: bool = True):
        self.output_dir = output_dir
        
        # Clean previous comparison run if requested
        if clean_start and os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
            print(f"Cleaned previous comparison from {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.task_definition = """
Design and implement a new API endpoint: GET /api/user/preferences

Requirements:
- Return user preference settings (theme, language, timezone, notifications)
- Requires authentication
- Handle error cases appropriately
- Provide both backend (Python/Flask) and frontend (TypeScript) implementations
"""
        
        self.results = {
            "multi_agent_coordinated": None,
            "single_agent": None,
            "independent_agents": None
        }
    
    def run_single_agent_approach(self) -> dict:
        """Single agent does everything"""
        print("\n" + "="*60)
        print("APPROACH 1: Single Agent (No Coordination)")
        print("="*60)
        
        prompt = f"""You are tasked with designing and implementing a complete API feature.

TASK:
{self.task_definition}

DELIVERABLES:
1. API contract specification (endpoint, request/response format, errors)
2. Backend implementation (Python/Flask)
3. Frontend implementation (TypeScript/JavaScript)

Provide all three components. Focus on core functionality - avoid extras like Docker, extensive deployment docs, or build configurations.
"""
        
        start_time = datetime.now()
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        response = message.content[0].text
        
        result = {
            "approach": "single_agent",
            "output": response,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
            "duration_seconds": duration,
            "cost_usd": (message.usage.input_tokens / 1_000_000 * 3.0) + 
                       (message.usage.output_tokens / 1_000_000 * 15.0),
            "agent_calls": 1
        }
        
        # Save output
        output_path = os.path.join(self.output_dir, "single_agent_output.md")
        with open(output_path, 'w') as f:
            f.write(f"# Single Agent Approach\n\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write(f"Cost: ${result['cost_usd']:.4f}\n\n")
            f.write(response)
        
        print(f"✓ Complete in {duration:.2f}s")
        print(f"  Tokens: {result['total_tokens']:,} | Cost: ${result['cost_usd']:.4f}")
        
        self.results["single_agent"] = result
        return result
    
    def run_independent_agents_approach(self) -> dict:
        """Three agents work independently without coordination"""
        print("\n" + "="*60)
        print("APPROACH 2: Independent Agents (No State Sharing)")
        print("="*60)
        
        agents = [
            {
                "name": "API Designer",
                "task": "Design an API contract for GET /api/user/preferences. Define endpoint, authentication, request/response format, and error cases."
            },
            {
                "name": "Backend Developer", 
                "task": "Implement a Python/Flask backend for GET /api/user/preferences that returns user preferences (theme, language, timezone, notifications). Include authentication and error handling."
            },
            {
                "name": "Frontend Developer",
                "task": "Implement a TypeScript/JavaScript client to call GET /api/user/preferences. Handle authentication, parse the response, and handle errors."
            }
        ]
        
        outputs = []
        total_input_tokens = 0
        total_output_tokens = 0
        start_time = datetime.now()
        
        for agent in agents:
            print(f"  Running {agent['name']}...")
            
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                messages=[{"role": "user", "content": agent['task']}]
            )
            
            outputs.append({
                "agent": agent['name'],
                "output": message.content[0].text
            })
            
            total_input_tokens += message.usage.input_tokens
            total_output_tokens += message.usage.output_tokens
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "approach": "independent_agents",
            "outputs": outputs,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "duration_seconds": duration,
            "cost_usd": (total_input_tokens / 1_000_000 * 3.0) + 
                       (total_output_tokens / 1_000_000 * 15.0),
            "agent_calls": 3
        }
        
        # Save outputs
        output_path = os.path.join(self.output_dir, "independent_agents_output.md")
        with open(output_path, 'w') as f:
            f.write(f"# Independent Agents Approach\n\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write(f"Cost: ${result['cost_usd']:.4f}\n\n")
            for output in outputs:
                f.write(f"## {output['agent']}\n\n")
                f.write(output['output'])
                f.write("\n\n")
        
        print(f"✓ Complete in {duration:.2f}s")
        print(f"  Tokens: {result['total_tokens']:,} | Cost: ${result['cost_usd']:.4f}")
        
        self.results["independent_agents"] = result
        return result
    
    def load_coordinated_results(self, orchestrator_summary_path: str = "./poc_output/debug/execution_summary.json") -> dict:
        """Load results from the coordinated multi-agent run"""
        print("\n" + "="*60)
        print("APPROACH 3: Multi-Agent Coordinated (State Files)")
        print("="*60)
        
        if not os.path.exists(orchestrator_summary_path):
            print("  Error: Run orchestrator.py first to generate coordinated results")
            return None
        
        with open(orchestrator_summary_path, 'r') as f:
            summary = json.load(f)
        
        cost_analysis = summary.get("cost_analysis", {})
        
        result = {
            "approach": "multi_agent_coordinated",
            "input_tokens": cost_analysis.get("total_input_tokens", 0),
            "output_tokens": cost_analysis.get("total_output_tokens", 0),
            "total_tokens": cost_analysis.get("total_tokens", 0),
            "cost_usd": cost_analysis.get("total_cost_usd", 0),
            "iterations": summary.get("total_iterations", 0),
            "completed_subtasks": summary.get("completed_subtasks", []),
            "all_complete": summary.get("final_state", {}).get("all_complete", False)
        }
        
        print(f"✓ Loaded results")
        print(f"  Tokens: {result['total_tokens']:,} | Cost: ${result['cost_usd']:.4f}")
        
        self.results["multi_agent_coordinated"] = result
        return result
    
    def evaluate_outputs(self) -> dict:
        """Use AI to evaluate quality and compatibility of outputs"""
        print("\n" + "="*60)
        print("EVALUATING OUTPUTS")
        print("="*60)
        
        # Load all outputs
        single_agent_output = ""
        if os.path.exists(os.path.join(self.output_dir, "single_agent_output.md")):
            with open(os.path.join(self.output_dir, "single_agent_output.md"), 'r') as f:
                single_agent_output = f.read()
        
        independent_agents_output = ""
        if os.path.exists(os.path.join(self.output_dir, "independent_agents_output.md")):
            with open(os.path.join(self.output_dir, "independent_agents_output.md"), 'r') as f:
                independent_agents_output = f.read()
        
        coordinated_outputs = {}
        state_dir = "./poc_output/state"
        if os.path.exists(state_dir):
            for filename in os.listdir(state_dir):
                if filename.endswith('.md'):
                    with open(os.path.join(state_dir, filename), 'r') as f:
                        coordinated_outputs[filename] = f.read()
        
        # Build coordinated outputs section
        coordinated_section = ""
        for k, v in coordinated_outputs.items():
            coordinated_section += f"## {k}\n{v[:2000]}\n"
        
        eval_prompt = f"""You are evaluating three different approaches to building the same API feature.

TASK: {self.task_definition}

# APPROACH 1: Single Agent
{single_agent_output[:5000]}
...

# APPROACH 2: Independent Agents (no coordination)
{independent_agents_output[:5000]}
...

# APPROACH 3: Multi-Agent Coordinated (state file coordination)
{coordinated_section}

# EVALUATION CRITERIA

For each approach, rate on a scale of 1-10:

1. **Completeness**: Are all three components (API contract, backend, frontend) present and functional?

2. **Compatibility**: Do the components work together? 
   - Does backend match the API contract?
   - Does frontend match the API contract?
   - Would this actually work in production?

3. **Code Quality**: 
   - Proper error handling
   - Production-ready vs prototype
   - Security considerations

4. **Efficiency**: 
   - Appropriate scope (not over-engineered)
   - No missing critical pieces
   - No redundant code

5. **Consistency**:
   - Naming conventions aligned
   - Data structures consistent
   - Error handling patterns consistent

Provide scores and detailed reasoning for each approach. Then answer:
- Which approach produced the BEST output overall?
- What are the key differences in output quality?
- Does coordination provide measurable benefit?

Be specific and reference actual examples from the code.
"""
        
        print("  Calling AI evaluator...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=6000,
            messages=[{"role": "user", "content": eval_prompt}]
        )
        
        evaluation = message.content[0].text
        
        # Save evaluation
        eval_path = os.path.join(self.output_dir, "quality_comparison.md")
        with open(eval_path, 'w') as f:
            f.write("# Quality Comparison Evaluation\n\n")
            f.write(evaluation)
        
        print(f"✓ Evaluation complete")
        print(f"  Saved to {eval_path}")
        
        return evaluation
    
    def generate_summary(self):
        """Generate comparison summary"""
        summary_path = os.path.join(self.output_dir, "comparison_summary.md")
        
        with open(summary_path, 'w') as f:
            f.write("# Coordination Approach Comparison\n\n")
            f.write("## Cost & Efficiency Metrics\n\n")
            f.write("| Approach | Tokens | Cost (USD) | Agent Calls |\n")
            f.write("|----------|--------|------------|-------------|\n")
            
            for approach, result in self.results.items():
                if result:
                    approach_name = approach.replace('_', ' ').title()
                    tokens = result.get('total_tokens', 0)
                    cost = result.get('cost_usd', 0)
                    calls = result.get('agent_calls', result.get('iterations', 0))
                    f.write(f"| {approach_name} | {tokens:,} | ${cost:.4f} | {calls} |\n")
            
            f.write("\n## Key Findings\n\n")
            f.write("See `quality_comparison.md` for detailed quality analysis.\n\n")
            
            # Calculate differences
            if self.results["single_agent"] and self.results["multi_agent_coordinated"]:
                single_cost = self.results["single_agent"]["cost_usd"]
                coord_cost = self.results["multi_agent_coordinated"]["cost_usd"]
                cost_diff = ((coord_cost - single_cost) / single_cost) * 100
                
                f.write(f"### Cost Comparison\n")
                f.write(f"- Multi-agent coordination cost: ${coord_cost:.4f}\n")
                f.write(f"- Single agent cost: ${single_cost:.4f}\n")
                f.write(f"- Difference: {cost_diff:+.1f}%\n\n")
        
        print(f"\n{'='*60}")
        print(f"Summary saved to {summary_path}")
        print(f"{'='*60}\n")
    
    def run_full_comparison(self):
        """Run all approaches and compare"""
        print("\n" + "="*60)
        print("COORDINATION COMPARISON EXPERIMENT")
        print("="*60)
        
        # Run single agent
        self.run_single_agent_approach()
        
        # Run independent agents
        self.run_independent_agents_approach()
        
        # Load coordinated results (assumes orchestrator already ran)
        self.load_coordinated_results()
        
        # Evaluate outputs
        self.evaluate_outputs()
        
        # Generate summary
        self.generate_summary()
        
        print("\n" + "="*60)
        print("COMPARISON COMPLETE")
        print("="*60)
        print("\nResults saved to ./comparison_output/")
        print("\nKey files:")
        print("  - comparison_summary.md - Cost and efficiency metrics")
        print("  - quality_comparison.md - AI evaluation of output quality")
        print("  - single_agent_output.md - Single agent results")
        print("  - independent_agents_output.md - Independent agents results")


if __name__ == "__main__":
    # clean_start=True ensures fresh comparison each run
    comparison = CoordinationComparison(clean_start=True)
    comparison.run_full_comparison()
