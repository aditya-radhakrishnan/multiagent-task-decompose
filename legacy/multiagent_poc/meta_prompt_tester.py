"""
Test whether AI can correctly decide when to decompose tasks
"""

import json
import os
import anthropic
from task_generator import SIMPLE_TASKS, MEDIUM_TASKS, COMPLEX_TASKS

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


class MetaPromptTester:
    """Test meta-prompt routing decisions"""
    
    def __init__(self, output_dir: str = "./meta_prompt_test"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.decisions = []
        
        # Ground truth from our experiments
        self.ground_truth = {
            "simple_1": "SINGLE_AGENT",  # Todo API - simple, cohesive
            "simple_2": "SINGLE_AGENT",  # Weather dashboard
            "medium_1": "SINGLE_AGENT",  # Auth system (after seeing extended thinking results)
            "medium_2": "DECOMPOSE",     # Payment integration - might have separate concerns
            "complex_1": "SINGLE_AGENT", # E-commerce - tightly coupled despite complexity
            "complex_3": "DECOMPOSE",    # Analytics - might have separate data/viz concerns
        }
    
    def make_decision(self, task_id: str, task_name: str, task_description: str) -> dict:
        """Use meta-prompt to decide decomposition strategy"""
        
        prompt = f"""You are a task routing system that decides whether a software engineering task should be handled by a single agent or decomposed into multiple coordinated agents.

TASK TO ANALYZE:
{task_description}

DECISION FRAMEWORK:

Consider these factors in your analysis:

**1. OUTPUT SIZE CONSTRAINT**
Would implementing all components require >8,000 tokens of code output? Large systems (multiple services, frontends, complex backends) may exceed single-agent output capacity, causing truncation. If the implementation would likely need >8k tokens, decomposition helps avoid incomplete output.

**2. ARCHITECTURAL BOUNDARIES**
Are there natural separation points?
- Different deployment units (separate services, microservices)
- Different technology stacks with clear API contracts
- Distinct user types requiring separate interfaces (customer vs admin vs public API)
- Independent scaling or security requirements
- Separate databases or state management

**3. COUPLING ANALYSIS**
How tightly integrated are the components?
- Do they share authentication/authorization systems?
- Do they share data models, types, business logic?
- Do they share a single database schema?
- Is there natural code reuse across components?
High coupling suggests single agent benefits from unified context.

**4. COORDINATION OVERHEAD**
Is the decomposition overhead justified?
- Simple full-stack apps: overhead often exceeds benefits
- Complex multi-service systems: coordination enables modularity and parallel work
- Consider: Would separate teams typically work on these components?

**GENERAL PRINCIPLES:**

Use SINGLE_AGENT when:
- Total implementation fits comfortably in 8k tokens
- Components are tightly coupled with shared infrastructure
- Natural code reuse is important
- Standard monolithic web application pattern
- The system is cohesive (single product/service)

Use DECOMPOSE when:
- Implementation likely exceeds 8k tokens (risk of truncation)
- Components have clear architectural boundaries
- Different deployment units or tech stacks
- Multiple distinct user interfaces or services
- Components could be developed independently
- True microservices or multi-service architecture

Analyze this task using these general principles. Your reasoning should apply to similar tasks, not just this specific one.

Respond in JSON format:
{{
  "decision": "SINGLE_AGENT" or "DECOMPOSE",
  "confidence": "low" | "medium" | "high",
  "reasoning": "General explanation that could apply to similar tasks",
  "key_factors": ["factor1", "factor2", "factor3"],
  "estimated_output_tokens": "approximate range (e.g., '5-7k' or '15-20k')"
}}

Provide only the JSON, no other text.
"""
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response = message.content[0].text
        
        # Parse JSON
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            decision_data = json.loads(json_match.group())
        else:
            decision_data = {
                "decision": "SINGLE_AGENT",
                "confidence": "low",
                "reasoning": "Parse error",
                "key_factors": [],
                "estimated_output_tokens": "unknown"
            }
        
        return decision_data
    
    def test_task(self, task_id: str, task_name: str, task_description: str, complexity: str):
        """Test decision on a single task"""
        print(f"\n{'='*60}")
        print(f"Testing: {task_id} - {task_name}")
        print(f"Complexity: {complexity}")
        print(f"{'='*60}")
        
        # Get AI decision
        decision_data = self.make_decision(task_id, task_name, task_description)
        
        # Check against ground truth
        expected = self.ground_truth.get(task_id, "UNKNOWN")
        actual = decision_data["decision"]
        correct = (expected == actual) if expected != "UNKNOWN" else None
        
        result = {
            "task_id": task_id,
            "task_name": task_name,
            "complexity": complexity,
            "expected": expected,
            "actual": actual,
            "correct": correct,
            "confidence": decision_data["confidence"],
            "reasoning": decision_data["reasoning"],
            "key_factors": decision_data["key_factors"]
        }
        
        self.decisions.append(result)
        
        # Print result
        status = "✓" if correct else "✗" if correct is False else "?"
        print(f"  Expected: {expected}")
        print(f"  Actual:   {actual} ({decision_data['confidence']} confidence)")
        print(f"  {status} {'CORRECT' if correct else 'INCORRECT' if correct is False else 'NO GROUND TRUTH'}")
        print(f"  Reasoning: {decision_data['reasoning']}")
        
        return result
    
    def run_tests(self):
        """Run tests on selected tasks"""
        print("\n" + "="*60)
        print("META-PROMPT DECISION TESTING")
        print("="*60)
        print("Testing whether AI can correctly route tasks...")
        
        # Test subset of tasks
        test_cases = [
            # Simple tasks
            (SIMPLE_TASKS[0], "simple"),
            (SIMPLE_TASKS[1], "simple"),
            
            # Medium tasks
            (MEDIUM_TASKS[0], "medium"),
            (MEDIUM_TASKS[1], "medium"),
            
            # Complex tasks
            (COMPLEX_TASKS[0], "complex"),
            (COMPLEX_TASKS[2], "complex"),
        ]
        
        for task, complexity in test_cases:
            self.test_task(task["id"], task["name"], task["description"], complexity)
        
        # Calculate accuracy
        self.print_summary()
        self.save_results()
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        # Filter decisions with ground truth
        evaluated = [d for d in self.decisions if d["correct"] is not None]
        
        if not evaluated:
            print("No ground truth available for evaluation")
            return
        
        correct = sum(1 for d in evaluated if d["correct"])
        total = len(evaluated)
        accuracy = (correct / total * 100) if total > 0 else 0
        
        print(f"\nAccuracy: {correct}/{total} ({accuracy:.1f}%)")
        
        # Breakdown by complexity
        for complexity in ["simple", "medium", "complex"]:
            comp_decisions = [d for d in evaluated if d["complexity"] == complexity]
            if comp_decisions:
                comp_correct = sum(1 for d in comp_decisions if d["correct"])
                comp_total = len(comp_decisions)
                comp_accuracy = (comp_correct / comp_total * 100) if comp_total > 0 else 0
                print(f"  {complexity.capitalize()}: {comp_correct}/{comp_total} ({comp_accuracy:.1f}%)")
        
        # Show errors
        errors = [d for d in evaluated if not d["correct"]]
        if errors:
            print(f"\nErrors ({len(errors)}):")
            for d in errors:
                print(f"  - {d['task_id']}: Expected {d['expected']}, got {d['actual']}")
                print(f"    Reasoning: {d['reasoning']}")
    
    def save_results(self):
        """Save results to JSON"""
        results_path = os.path.join(self.output_dir, "meta_prompt_results.json")
        
        with open(results_path, 'w') as f:
            json.dump({
                "total_tests": len(self.decisions),
                "decisions": self.decisions,
                "summary": {
                    "correct": sum(1 for d in self.decisions if d["correct"]),
                    "total_evaluated": sum(1 for d in self.decisions if d["correct"] is not None)
                }
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_path}")
        
        # Also save markdown report
        self.save_markdown_report()
    
    def save_markdown_report(self):
        """Generate readable markdown report"""
        report_path = os.path.join(self.output_dir, "decision_analysis.md")
        
        with open(report_path, 'w') as f:
            f.write("# Meta-Prompt Decision Analysis\n\n")
            
            f.write("## Test Results\n\n")
            f.write("| Task | Complexity | Expected | Actual | Correct | Confidence |\n")
            f.write("|------|-----------|----------|--------|---------|------------|\n")
            
            for d in self.decisions:
                status = "✓" if d["correct"] else "✗" if d["correct"] is False else "?"
                f.write(f"| {d['task_name']} | {d['complexity']} | {d['expected']} | {d['actual']} | {status} | {d['confidence']} |\n")
            
            f.write("\n## Decision Reasoning\n\n")
            
            for d in self.decisions:
                f.write(f"### {d['task_name']} ({d['task_id']})\n\n")
                f.write(f"**Decision:** {d['actual']} ({d['confidence']} confidence)\n\n")
                f.write(f"**Reasoning:** {d['reasoning']}\n\n")
                f.write(f"**Key Factors:**\n")
                for factor in d['key_factors']:
                    f.write(f"- {factor}\n")
                f.write("\n")
                
                if d['correct'] is not None:
                    status = "✓ Correct" if d['correct'] else "✗ Incorrect"
                    f.write(f"**Ground Truth:** {d['expected']} - {status}\n\n")
                
                f.write("---\n\n")
        
        print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    tester = MetaPromptTester()
    tester.run_tests()
