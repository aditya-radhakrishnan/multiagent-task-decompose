import os
import json
from datetime import datetime
from typing import Dict, List, Any
import anthropic

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class AgentOrchestrator:
    def __init__(self, output_dir: str = "./poc_output", clean_start: bool = True):
        self.output_dir = output_dir
        self.state_dir = os.path.join(output_dir, "state")
        self.artifacts_dir = os.path.join(output_dir, "artifacts")
        self.debug_dir = os.path.join(output_dir, "debug")
        
        # Clean previous run if requested
        if clean_start and os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
            print(f"Cleaned previous run from {output_dir}")
        
        # Create directories
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.artifacts_dir, exist_ok=True)
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # Track subtask completion and execution history
        self.completed_subtasks = set()
        self.execution_log = []
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        # Pricing for claude-sonnet-4-5-20250929 (as of Oct 2025)
        # $3 per million input tokens, $15 per million output tokens
        self.input_price_per_million = 3.0
        self.output_price_per_million = 15.0
        
    def define_task(self) -> Dict[str, Any]:
        """Define the main task and subtasks"""
        return {
            "main_task": "Add a GET /api/user/preferences endpoint that returns user preference settings",
            "subtasks": [
                {
                    "id": "A",
                    "name": "api_contract",
                    "description": "Design the API contract for the /api/user/preferences endpoint. Define the HTTP method, path, request parameters, response schema, and error cases.",
                },
                {
                    "id": "B", 
                    "name": "backend",
                    "description": "Implement the backend endpoint in Python/Flask. Should follow the API contract and include proper error handling.",
                    "depends_on": ["A"]
                },
                {
                    "id": "C",
                    "name": "frontend",
                    "description": "Implement a TypeScript/JavaScript function to call the API endpoint. Should handle the response and errors properly.",
                    "depends_on": ["A"]
                }
            ]
        }
    
    def read_all_state_files(self) -> str:
        """Read all state files and return as concatenated string"""
        state_context = []
        
        for filename in sorted(os.listdir(self.state_dir)):
            if filename.endswith('.md'):
                filepath = os.path.join(self.state_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                    state_context.append(f"=== {filename} ===\n{content}\n")
        
        if not state_context:
            return "No state files exist yet. You are the first to start."
        
        return "\n".join(state_context)
    
    def write_state_file(self, subtask_id: str, content: str):
        """Write subtask state to file"""
        filename = f"subtask_{subtask_id}_state.md"
        filepath = os.path.join(self.state_dir, filename)
        
        timestamp = datetime.now().isoformat()
        full_content = f"# Subtask {subtask_id} State\n"
        full_content += f"Last Updated: {timestamp}\n\n"
        full_content += content
        
        with open(filepath, 'w') as f:
            f.write(full_content)
    
    def build_prompt(self, subtask: Dict[str, Any], context: str, iteration: int, max_iterations: int) -> str:
        """Build the prompt for a subtask agent"""
        prompt = f"""You are an AI agent working on a software engineering task as part of a team of agents.

MAIN TASK: {self.define_task()['main_task']}

YOUR SUBTASK (ID: {subtask['id']}):
{subtask['description']}

ITERATION INFO:
- Current iteration: {iteration + 1} of {max_iterations}
- Remaining iterations: {max_iterations - iteration - 1}
- Strategy: Focus on CORE requirements first. If you're on later iterations, prioritize completion over perfection.

CURRENT STATE FROM ALL SUBTASKS:
{context}

---

INSTRUCTIONS:

1. Review the current state from all subtasks above
2. Determine if you have the information you need to proceed
3. If blocked waiting for another subtask, clearly state what you're waiting for
4. If you can make progress, do the work
5. Declare your status clearly at the end

SCOPE GUIDELINES:
For subtask A (API contract): Define the complete API specification with endpoint, request/response format, and error cases
For subtask B (backend): Write Python/Flask code that implements the API contract. Include basic error handling. DO NOT add extras like Docker, K8s, or extensive deployment docs unless explicitly requested.
For subtask C (frontend): Write TypeScript/JavaScript code that calls the API. Include basic error handling. DO NOT add extras like build configs, linters, or testing frameworks unless explicitly requested.

COMPLETION CRITERIA - You are COMPLETE when:
✓ Core functionality is implemented
✓ Your code matches dependencies (like Agent A's API contract)
✓ Basic error handling is included
✓ No critical functionality is missing

DO NOT add "nice-to-have" features like:
- Extensive deployment configurations
- Multiple testing frameworks
- Build tool configurations  
- Linting/formatting configs
- Example applications beyond a simple demo

Focus on the MINIMUM VIABLE IMPLEMENTATION that fulfills the requirements.

---

CRITICAL - STATUS DECLARATION:

Your response MUST end with EXACTLY ONE of these status declarations:

STATUS: BLOCKED
[Use this if you're waiting for another agent to finish their work]

STATUS: IN_PROGRESS
[Use this if you can work but haven't finished yet]

STATUS: COMPLETE
[Use this if you have fulfilled the completion criteria above]

The status line must be the LAST line of your response.
"""
        return prompt
    
    def is_complete(self, response: str) -> bool:
        """Check if agent declares task complete"""
        return "STATUS: COMPLETE" in response.upper()
    
    def is_blocked(self, response: str) -> bool:
        """Check if agent is blocked"""
        return "STATUS: BLOCKED" in response.upper()
    
    def log_prompt(self, subtask_id: str, iteration: int, prompt: str):
        """Save prompt to debug directory"""
        filename = f"subtask_{subtask_id}_iter_{iteration}_prompt.txt"
        filepath = os.path.join(self.debug_dir, filename)
        with open(filepath, 'w') as f:
            f.write(prompt)
    
    def log_response(self, subtask_id: str, iteration: int, response: str):
        """Save response to debug directory"""
        filename = f"subtask_{subtask_id}_iter_{iteration}_response.txt"
        filepath = os.path.join(self.debug_dir, filename)
        with open(filepath, 'w') as f:
            f.write(response)
    
    def log_execution_event(self, iteration: int, subtask_id: str, status: str, notes: str = ""):
        """Log an execution event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "iteration": iteration,
            "subtask_id": subtask_id,
            "status": status,
            "notes": notes
        }
        self.execution_log.append(event)
    
    def save_execution_summary(self):
        """Save a summary of the entire execution"""
        summary_path = os.path.join(self.debug_dir, "execution_summary.json")
        
        # Calculate costs
        input_cost = (self.total_input_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (self.total_output_tokens / 1_000_000) * self.output_price_per_million
        total_cost = input_cost + output_cost
        
        summary = {
            "run_timestamp": datetime.now().isoformat(),
            "total_iterations": len(set(e["iteration"] for e in self.execution_log)),
            "completed_subtasks": list(self.completed_subtasks),
            "execution_log": self.execution_log,
            "final_state": {
                "all_complete": len(self.completed_subtasks) == len(self.define_task()['subtasks'])
            },
            "cost_analysis": {
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "input_cost_usd": round(input_cost, 4),
                "output_cost_usd": round(output_cost, 4),
                "total_cost_usd": round(total_cost, 4)
            }
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Also create a human-readable markdown summary
        md_summary_path = os.path.join(self.debug_dir, "execution_summary.md")
        with open(md_summary_path, 'w') as f:
            f.write("# Execution Summary\n\n")
            f.write(f"**Run Time:** {summary['run_timestamp']}\n\n")
            f.write(f"**Total Iterations:** {summary['total_iterations']}\n\n")
            f.write(f"**Completed Subtasks:** {', '.join(self.completed_subtasks) if self.completed_subtasks else 'None'}\n\n")
            f.write(f"**All Tasks Complete:** {'Yes' if summary['final_state']['all_complete'] else 'No'}\n\n")
            
            f.write("## Cost Analysis\n\n")
            f.write(f"- **Total Input Tokens:** {self.total_input_tokens:,}\n")
            f.write(f"- **Total Output Tokens:** {self.total_output_tokens:,}\n")
            f.write(f"- **Total Tokens:** {self.total_input_tokens + self.total_output_tokens:,}\n")
            f.write(f"- **Input Cost:** ${input_cost:.4f}\n")
            f.write(f"- **Output Cost:** ${output_cost:.4f}\n")
            f.write(f"- **Total Cost:** ${total_cost:.4f}\n\n")
            
            f.write("## Execution Timeline\n\n")
            for event in self.execution_log:
                f.write(f"- **Iter {event['iteration']}** - Subtask {event['subtask_id']}: {event['status']}")
                if event['notes']:
                    f.write(f" - {event['notes']}")
                f.write("\n")
    
    def call_agent(self, subtask: Dict[str, Any], context: str, iteration: int, max_iterations: int) -> str:
        """Call Claude to work on a subtask"""
        prompt = self.build_prompt(subtask, context, iteration, max_iterations)
        
        # Log the full prompt for debugging
        self.log_prompt(subtask['id'], iteration, prompt)
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=6000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Track token usage
        self.total_input_tokens += message.usage.input_tokens
        self.total_output_tokens += message.usage.output_tokens
        
        response = message.content[0].text
        
        # Log the full response for debugging
        self.log_response(subtask['id'], iteration, response)
        
        # Log token usage for this call
        print(f"Tokens: {message.usage.input_tokens} in, {message.usage.output_tokens} out")
        
        return response
    
    def run(self, max_iterations: int = 5):
        """Main orchestration loop"""
        task_def = self.define_task()
        subtasks = task_def['subtasks']
        
        print(f"Starting Agent Coordination PoC")
        print(f"Main Task: {task_def['main_task']}")
        print(f"Subtasks: {len(subtasks)}")
        print(f"Output Directory: {self.output_dir}\n")
        
        for iteration in range(max_iterations):
            print(f"\n{'='*60}")
            print(f"ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'='*60}\n")
            
            all_complete = True
            
            for subtask in subtasks:
                subtask_id = subtask['id']
                
                # Skip if already complete
                if subtask_id in self.completed_subtasks:
                    print(f"[Subtask {subtask_id}] Already complete, skipping")
                    self.log_execution_event(iteration, subtask_id, "SKIPPED", "Already complete")
                    continue
                
                all_complete = False
                
                print(f"\n[Subtask {subtask_id}] {subtask['name']}")
                print(f"Description: {subtask['description']}")
                
                # Read current state
                context = self.read_all_state_files()
                
                # Call agent
                print(f"Calling agent...")
                response = self.call_agent(subtask, context, iteration, max_iterations)
                
                # Write state
                self.write_state_file(subtask_id, response)
                print(f"State written to: subtask_{subtask_id}_state.md")
                
                # Check status
                if self.is_complete(response):
                    self.completed_subtasks.add(subtask_id)
                    print(f"✓ Subtask {subtask_id} marked COMPLETE")
                    self.log_execution_event(iteration, subtask_id, "COMPLETE")
                elif self.is_blocked(response):
                    print(f"⧗ Subtask {subtask_id} is BLOCKED")
                    self.log_execution_event(iteration, subtask_id, "BLOCKED")
                else:
                    print(f"→ Subtask {subtask_id} in progress")
                    self.log_execution_event(iteration, subtask_id, "IN_PROGRESS")
            
            if all_complete:
                print(f"\n{'='*60}")
                print("ALL SUBTASKS COMPLETE!")
                print(f"{'='*60}")
                break
        
        # Save execution summary
        self.save_execution_summary()
        
        # Calculate final costs
        input_cost = (self.total_input_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (self.total_output_tokens / 1_000_000) * self.output_price_per_million
        total_cost = input_cost + output_cost
        
        print(f"\nPoC run complete. Check {self.output_dir} for results.")
        print(f"Debug information saved to {self.debug_dir}")
        print(f"\n{'='*60}")
        print("COST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Input Tokens:  {self.total_input_tokens:,}")
        print(f"Total Output Tokens: {self.total_output_tokens:,}")
        print(f"Total Tokens:        {self.total_input_tokens + self.total_output_tokens:,}")
        print(f"")
        print(f"Input Cost:          ${input_cost:.4f}")
        print(f"Output Cost:         ${output_cost:.4f}")
        print(f"Total Cost:          ${total_cost:.4f}")
        print(f"{'='*60}")
        print(f"\nKey files to review:")
        print(f"  - {self.debug_dir}/execution_summary.md - Human-readable timeline + costs")
        print(f"  - {self.state_dir}/ - Final state of each subtask")
        print(f"  - {self.debug_dir}/ - Full prompts and responses for each iteration")


if __name__ == "__main__":
    # clean_start=True ensures fresh state for each run
    orchestrator = AgentOrchestrator(clean_start=True)
    orchestrator.run(max_iterations=5)
