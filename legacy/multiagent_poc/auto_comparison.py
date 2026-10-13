import os
import json
from datetime import datetime
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class AutoDecompositionComparison:
    """
    Compare automatic task decomposition + coordination vs single agent
    """
    
    def __init__(self, output_dir: str = "./auto_comparison_output", clean_start: bool = True):
        self.output_dir = output_dir
        
        if clean_start and os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
            print(f"Cleaned previous comparison from {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.results = {
            "auto_decomposition": None,
            "single_agent": None
        }
    
    def load_checkpoint(self):
        """Load previous results from checkpoint if available"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                    self.results = checkpoint.get("results", self.results)
                    print(f"✓ Loaded checkpoint from previous run")
                    if self.results.get("multi_agent_coordinated"):
                        print("  - Multi-agent results found")
                    if self.results.get("single_agent"):
                        print("  - Single agent results found")
            except Exception as e:
                print(f"Warning: Could not load checkpoint: {e}")
    
    def save_checkpoint(self):
        """Save current results to checkpoint"""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "results": self.results
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save checkpoint: {e}")
    
    def run_single_agent(self, task_description: str) -> dict:
        """Run single agent approach with extended thinking"""
        print("\n" + "="*60)
        print("APPROACH 1: Single Agent (with Extended Thinking)")
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
        
        # Extract text from response (handle both thinking and text blocks)
        response = ""
        for block in message.content:
            if hasattr(block, 'text'):
                response += block.text
            elif hasattr(block, 'type') and block.type == 'text':
                response += block.text if hasattr(block, 'text') else ""
        
        # Fallback if no text extracted
        if not response and len(message.content) > 0:
            # Try accessing as dict or direct attribute
            try:
                response = message.content[0].text
            except (AttributeError, IndexError):
                response = str(message.content)
        
        result = {
            "approach": "single_agent",
            "output": response,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
            "duration_seconds": duration,
            "cost_usd": (message.usage.input_tokens / 1_000_000 * 3.0) + 
                       (message.usage.output_tokens / 1_000_000 * 15.0),
            "agent_calls": 1,
            "extended_thinking": True
        }
        
        # Save output
        output_path = os.path.join(self.output_dir, "single_agent_output.md")
        with open(output_path, 'w') as f:
            f.write(f"# Single Agent Approach (with Extended Thinking)\n\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write(f"Cost: ${result['cost_usd']:.4f}\n\n")
            f.write(response)
        
        print(f"✓ Complete in {duration:.2f}s")
        print(f"  Tokens: {result['total_tokens']:,} | Cost: ${result['cost_usd']:.4f}")
        
        self.results["single_agent"] = result
        self.save_checkpoint()  # Save after single agent completes
        return result
    
    def load_auto_decomposition_results(self, auto_output_dir: str = "./auto_poc_output") -> dict:
        """Load results from auto-decomposition run"""
        print("\n" + "="*60)
        print("APPROACH 2: Auto-Decomposition + Coordination")
        print("="*60)
        
        summary_path = os.path.join(auto_output_dir, "debug", "execution_summary.json")
        
        if not os.path.exists(summary_path):
            print("  Error: Run auto_orchestrator.py first")
            return None
        
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        
        cost_analysis = summary.get("cost_analysis", {})
        
        result = {
            "approach": "auto_decomposition",
            "input_tokens": cost_analysis.get("total_input_tokens", 0),
            "output_tokens": cost_analysis.get("total_output_tokens", 0),
            "total_tokens": cost_analysis.get("total_tokens", 0),
            "cost_usd": cost_analysis.get("total_cost_usd", 0),
            "num_subtasks": summary.get("num_subtasks_generated", 0),
            "iterations": summary.get("total_iterations", 0),
            "completed_subtasks": summary.get("completed_subtasks", []),
            "all_complete": summary.get("final_state", {}).get("all_complete", False)
        }
        
        print(f"✓ Loaded results")
        print(f"  Subtasks: {result['num_subtasks']} | Iterations: {result['iterations']}")
        print(f"  Tokens: {result['total_tokens']:,} | Cost: ${result['cost_usd']:.4f}")
        
        self.results["auto_decomposition"] = result
        return result
    
    def evaluate_comparison(self, task_description: str) -> str:
        """Use AI to compare both approaches"""
        print("\n" + "="*60)
        print("EVALUATING APPROACHES")
        print("="*60)
        
        # Load single agent output
        single_agent_output = ""
        single_path = os.path.join(self.output_dir, "single_agent_output.md")
        if os.path.exists(single_path):
            with open(single_path, 'r') as f:
                single_agent_output = f.read()
        
        # Load auto-decomposition outputs
        auto_outputs = {}
        auto_state_dir = "./auto_poc_output/state"
        if os.path.exists(auto_state_dir):
            for filename in os.listdir(auto_state_dir):
                if filename.endswith('.md'):
                    with open(os.path.join(auto_state_dir, filename), 'r') as f:
                        auto_outputs[filename] = f.read()
        
        # Load decomposition info
        decomp_info = ""
        decomp_path = "./auto_poc_output/debug/task_decomposition.json"
        if os.path.exists(decomp_path):
            with open(decomp_path, 'r') as f:
                decomp_data = json.load(f)
                decomp_info = f"Reasoning: {decomp_data.get('reasoning', '')}\n\n"
                decomp_info += "Subtasks:\n"
                for st in decomp_data.get('subtasks', []):
                    decomp_info += f"- [{st['id']}] {st['name']}: {st['description']}\n"
        
        # Build comparison sections
        auto_section = decomp_info + "\n\n"
        for k, v in auto_outputs.items():
            auto_section += f"## {k}\n{v[:2000]}...\n\n"
        
        eval_prompt = f"""You are comparing two approaches to completing the same software engineering task.

TASK:
{task_description}

---

# APPROACH 1: Single Agent

{single_agent_output[:6000]}
...

---

# APPROACH 2: Auto-Decomposition + Coordination

{auto_section[:6000]}
...

---

# EVALUATION CRITERIA

Compare both approaches on:

## 1. Quality Metrics (Score each 1-10)

**Completeness**: Are all required components present and functional?

**Correctness**: Does the implementation actually work? Are there bugs or issues?

**Code Quality**: Error handling, structure, readability, production-readiness

**Consistency**: If multiple components, do they align properly?

## 2. Efficiency Metrics

**Cost**: Token usage and USD cost

**Time/Complexity**: How much orchestration overhead?

**Simplicity**: Is the solution appropriately simple or over-engineered?

## 3. Decomposition Analysis (for Approach 2 only)

**Was the decomposition sensible?**
- Right number of subtasks?
- Clear separation of concerns?
- Dependencies correctly identified?

**Did coordination work?**
- Did agents wait for dependencies?
- Were outputs compatible?
- Any coordination failures?

## 4. Direct Comparison

For THIS specific task:
- Which approach produced better output?
- Which was more cost-effective?
- Which was more efficient?
- When would the other approach be better?

## 5. Key Insights

- What are the trade-offs between these approaches?
- When does auto-decomposition provide value?
- When is a single agent preferable?
- How does task complexity affect the comparison?

## 6. Final Verdict

**Winner**: [Approach 1 or 2]
**Overall Scores**: 
- Approach 1: X/30 (sum of quality scores)
- Approach 2: X/30

**Recommendation**: For tasks like this, use [which approach] because...

Be specific and reference actual evidence from the implementations.
"""
        
        print("  Calling AI evaluator...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=6000,
            messages=[{"role": "user", "content": eval_prompt}]
        )
        
        evaluation = message.content[0].text
        
        eval_cost = (message.usage.input_tokens / 1_000_000 * 3.0) + \
                   (message.usage.output_tokens / 1_000_000 * 15.0)
        
        # Save evaluation
        eval_path = os.path.join(self.output_dir, "approach_comparison.md")
        with open(eval_path, 'w') as f:
            f.write("# Auto-Decomposition vs Single Agent Comparison\n\n")
            f.write(evaluation)
            f.write("\n\n---\n\n")
            f.write("## Cost Analysis\n\n")
            f.write("| Metric | Single Agent | Auto-Decomposition |\n")
            f.write("|--------|--------------|--------------------|\n")
            
            single = self.results.get("single_agent", {})
            auto = self.results.get("auto_decomposition", {})
            
            f.write(f"| Tokens | {single.get('total_tokens', 0):,} | {auto.get('total_tokens', 0):,} |\n")
            f.write(f"| Cost | ${single.get('cost_usd', 0):.4f} | ${auto.get('cost_usd', 0):.4f} |\n")
            f.write(f"| Agent Calls | {single.get('agent_calls', 0)} | {auto.get('num_subtasks', 0)} subtasks |\n")
            
            if auto.get('cost_usd', 0) > 0 and single.get('cost_usd', 0) > 0:
                overhead = ((auto['cost_usd'] - single['cost_usd']) / single['cost_usd']) * 100
                f.write(f"\n**Coordination Overhead**: {overhead:+.1f}%\n")
            
            total_eval_cost = eval_cost + single.get('cost_usd', 0) + auto.get('cost_usd', 0)
            f.write(f"\n**Total Experiment Cost** (both approaches + evaluation): ${total_eval_cost:.4f}\n")
        
        print(f"✓ Evaluation complete")
        print(f"  Saved to {eval_path}")
        
        return evaluation
    
    def generate_summary(self):
        """Generate summary report"""
        summary_path = os.path.join(self.output_dir, "summary.md")
        
        with open(summary_path, 'w') as f:
            f.write("# Automatic Decomposition Comparison Summary\n\n")
            
            single = self.results.get("single_agent", {})
            auto = self.results.get("auto_decomposition", {})
            
            f.write("## Quick Stats\n\n")
            f.write("| Approach | Tokens | Cost | Subtasks/Calls |\n")
            f.write("|----------|--------|------|----------------|\n")
            f.write(f"| Single Agent | {single.get('total_tokens', 0):,} | ${single.get('cost_usd', 0):.4f} | 1 |\n")
            f.write(f"| Auto-Decomposition | {auto.get('total_tokens', 0):,} | ${auto.get('cost_usd', 0):.4f} | {auto.get('num_subtasks', 0)} |\n")
            
            f.write("\n## Key Files\n\n")
            f.write("- `approach_comparison.md` - Detailed quality comparison\n")
            f.write("- `single_agent_output.md` - Single agent results\n")
            f.write("- `../auto_poc_output/state/` - Auto-decomposition results\n")
            f.write("- `../auto_poc_output/debug/task_decomposition.json` - How task was decomposed\n")
        
        print(f"\nSummary saved to {summary_path}")
    
    def run_full_comparison(self, task_description: str):
        """Run complete comparison with checkpointing"""
        print("\n" + "="*60)
        print("AUTO-DECOMPOSITION VS SINGLE AGENT COMPARISON")
        print("="*60)
        
        # Check what we need to run
        need_single_agent = self.results.get("single_agent") is None
        
        # Always try to load auto-decomposition results
        try:
            self.load_auto_decomposition_results()
        except Exception as e:
            print(f"\nError loading auto-decomposition results: {e}")
            print("Make sure auto-decomposition completed successfully")
            return
        
        # Run single agent if needed
        if need_single_agent:
            self.run_single_agent(task_description)
        else:
            print("\n✓ Single agent results loaded from checkpoint")
        
        # Evaluate
        self.evaluate_comparison(task_description)
        
        # Generate summary
        self.generate_summary()
        
        print("\n" + "="*60)
        print("COMPARISON COMPLETE")
        print("="*60)
        print(f"\nResults: {self.output_dir}/")
        print("  - approach_comparison.md - Detailed analysis")
        print("  - summary.md - Quick overview")


if __name__ == "__main__":
    import sys
    
    # Default task
    task = """
Design and implement a new API endpoint: GET /api/user/preferences

Requirements:
- Return user preference settings (theme, language, timezone, notifications)
- Requires authentication
- Handle error cases appropriately
- Provide both backend (Python/Flask) and frontend (TypeScript) implementations
"""
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "complex":
            task = """
Build a complete user authentication system with the following requirements:
- User registration with email verification
- Login with JWT tokens
- Password reset functionality
- Role-based access control (admin, user, guest)
- Rate limiting on authentication endpoints
- Audit logging of authentication events
- Both backend (Python/Flask) and frontend (React/TypeScript) implementations
"""
        elif sys.argv[1] == "ecommerce":
            task = """
Build a product catalog system with:
- Database schema for products, categories, and inventory
- Search functionality with filters (price range, category, rating)
- Product recommendation engine based on viewing history
- Admin dashboard for product management (CRUD operations)
- Public-facing product listing and detail pages
- Shopping cart integration
- Image upload and storage management
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
        elif sys.argv[1] == "payment":
            task = """
Build a payment processing system:
- Stripe payment integration for checkout
- Subscription management (monthly/annual plans)
- Payment history and receipts
- Webhook handling for payment events
- Admin dashboard for viewing transactions
- Refund processing
- Backend (Python/Flask) and frontend checkout flow (React/TypeScript)
"""
        elif sys.argv[1] == "analytics":
            task = """
Build a data analytics platform:
- Connect to multiple data sources (CSV, databases, APIs)
- Custom metric definitions and calculations
- Interactive charts and visualizations
- Dashboard builder with drag-and-drop widgets
- Scheduled reports via email
- Data export functionality
- User access control and sharing
- Backend (Python/Flask), Frontend (React/TypeScript), Database (PostgreSQL)
"""
    
    comparison = AutoDecompositionComparison(clean_start=True)
    comparison.run_full_comparison(task)
