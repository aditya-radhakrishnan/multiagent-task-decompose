import os
import json
from datetime import datetime
from typing import Dict, List, Any
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class AutoDecomposingOrchestrator:
    """
    Orchestrator that automatically decomposes tasks into subtasks
    and manages coordination between dynamically created agents.
    """
    
    def __init__(self, output_dir: str = "./auto_poc_output", clean_start: bool = True):
        self.output_dir = output_dir
        self.state_dir = os.path.join(output_dir, "state")
        self.debug_dir = os.path.join(output_dir, "debug")
        
        # Clean previous run if requested
        if clean_start and os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
            print(f"Cleaned previous run from {output_dir}")
        
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self.completed_subtasks = set()
        self.execution_log = []
        self.last_stop_reason = None
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.input_price_per_million = 3.0
        self.output_price_per_million = 15.0
        
        # Task decomposition
        self.main_task = None
        self.subtasks = []
    
    def decompose_task(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Use AI to automatically decompose a task into subtasks
        """
        print("\n" + "="*60)
        print("AUTOMATIC TASK DECOMPOSITION")
        print("="*60)
        print(f"\nMain Task: {task_description}\n")
        
        decomposition_prompt = f"""You are a task decomposition expert. Given a complex task, break it down into concrete subtasks that can be worked on by separate agents.

TASK TO DECOMPOSE:
{task_description}

INSTRUCTIONS:
1. Analyze the task and identify logical subtasks
2. Each subtask should be:
   - Concrete and actionable (not too abstract)
   - Independently achievable by an agent
   - Clear about what artifacts/outputs it produces
3. Identify dependencies between subtasks
4. **Strongly prefer 2-3 subtasks.** Only use 4+ if components are:
   - Truly independent (can be deployed separately)
   - Different specialized domains (e.g., ML model + API + mobile app)
   - Cannot reasonably be combined without loss of clarity
5. **Avoid artificial separation:** Do not split tightly-coupled concerns
   - Example: Don't separate "backend" from "security" - security is part of backend
   - Example: Don't separate "API contract" from "implementation" unless contract serves multiple consumers
6. Order subtasks by dependencies (foundational work first)

OUTPUT FORMAT (respond with valid JSON only):
{{
  "reasoning": "Brief explanation of your decomposition strategy",
  "subtasks": [
    {{
      "id": "A",
      "name": "short_name",
      "description": "What this agent should do and what output it produces",
      "depends_on": ["B", "C"],
      "estimated_complexity": "low|medium|high"
    }}
  ]
}}

Focus on software engineering tasks. Consider:
- For cohesive systems (auth, CRUD APIs), prefer 2 subtasks: Backend + Frontend
- Only separate contracts if they serve multiple consumers
- Combine related concerns: backend includes its own security, error handling, logging
- Only split when there's a natural deployment or technology boundary

DECOMPOSITION GUIDELINES:
- 2 subtasks: Standard for most full-stack features
- 3 subtasks: When adding a distinct third component (e.g., background worker, admin panel)
- 4+ subtasks: Only for systems with multiple independent services or very different tech stacks

EXAMPLES OF GOOD DECOMPOSITION:
- API endpoint task → 2 subtasks: [Backend with contract, Frontend]
- Auth system → 2 subtasks: [Backend with auth/security/audit, Frontend]
- E-commerce catalog → 3 subtasks: [Backend API, Admin dashboard, Public storefront]

EXAMPLES OF BAD DECOMPOSITION (avoid these):
- Separating "API contract" from "Backend implementation" for a single service
- Separating "Security" from "Backend" when security is integral
- Separating "Testing" as its own subtask instead of including in implementations

Provide only the JSON, no additional commentary.
"""
        
        print("Calling decomposition agent...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": decomposition_prompt}]
        )
        
        self.total_input_tokens += message.usage.input_tokens
        self.total_output_tokens += message.usage.output_tokens
        
        response = message.content[0].text
        
        # Parse JSON response
        try:
            # Find JSON in response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decomposition = json.loads(json_match.group())
            else:
                decomposition = json.loads(response)
            
            subtasks = decomposition.get("subtasks", [])
            reasoning = decomposition.get("reasoning", "")
            
            print(f"\nDecomposition Reasoning:\n{reasoning}\n")
            print(f"Generated {len(subtasks)} subtasks:")
            for subtask in subtasks:
                deps = subtask.get('depends_on', [])
                dep_str = f" (depends on: {', '.join(deps)})" if deps else " (no dependencies)"
                print(f"  [{subtask['id']}] {subtask['name']}{dep_str}")
            
            print(f"\n{'='*60}")
            print(f"DECOMPOSITION ANALYSIS")
            print(f"{'='*60}")
            print(f"Total subtasks: {len(subtasks)}")
            
            if len(subtasks) > 4:
                print(f"⚠️  WARNING: {len(subtasks)} subtasks may have high coordination overhead")
                print(f"   Consider: Tasks with >4 subtasks often fail due to complexity")
            
            # Estimate subtask complexity (rough heuristic based on description length)
            for subtask in subtasks:
                description = subtask.get("description", "")
                word_count = len(description.split())
                
                # Rough estimation:
                # <50 words = simple (~3-5k tokens output)
                # 50-100 words = medium (~5-10k tokens output)
                # >100 words = complex (~10-15k tokens output)
                
                if word_count < 50:
                    estimate = "3-5k tokens"
                    risk = "✓ Low"
                elif word_count < 100:
                    estimate = "5-10k tokens"
                    risk = "⚠️  Medium"
                else:
                    estimate = "10-15k tokens"
                    risk = "⚠️  HIGH - may truncate"
                
                print(f"  [{subtask['id']}] {subtask['name']}")
                print(f"      Description: {word_count} words → Est. {estimate}")
                print(f"      Risk: {risk}")
            
            print(f"{'='*60}\n")
            
            # Save decomposition
            decomp_path = os.path.join(self.debug_dir, "task_decomposition.json")
            with open(decomp_path, 'w') as f:
                json.dump(decomposition, f, indent=2)
            
            return subtasks
            
        except json.JSONDecodeError as e:
            print(f"Error parsing decomposition response: {e}")
            print(f"Response was: {response}")
            raise
    
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
        
        deps_str = ""
        if subtask.get('depends_on'):
            deps_str = f"\nDEPENDENCIES: This task depends on subtasks {', '.join(subtask['depends_on'])} completing first."
        
        prompt = f"""You are an AI agent working on a software engineering task as part of a team of agents.

MAIN TASK: {self.main_task}

YOUR SUBTASK (ID: {subtask['id']} - {subtask['name']}):
{subtask['description']}
{deps_str}

ITERATION INFO:
- Current iteration: {iteration + 1} of {max_iterations}
- Remaining iterations: {max_iterations - iteration - 1}
- Strategy: Focus on CORE requirements first.

CURRENT STATE FROM ALL SUBTASKS:
{context}

---

INSTRUCTIONS:

1. Review the current state from all subtasks above
2. Check if your dependencies are satisfied
3. If blocked, state what you're waiting for
4. If ready, implement your task
5. Declare your status clearly at the end

SCOPE GUIDELINES:
- Implement core functionality only
- Include basic error handling
- DO NOT add extras like extensive deployment docs, multiple build tools, or advanced configurations
- Focus on MINIMUM VIABLE IMPLEMENTATION

COMPLETION CRITERIA - You are COMPLETE when:
✓ Core functionality is implemented
✓ Your code matches dependencies (if any)
✓ Basic error handling is included
✓ No critical functionality is missing

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
    
    def call_agent(self, subtask: Dict[str, Any], context: str, iteration: int, max_iterations: int) -> str:
        """Call Claude to work on a subtask"""
        prompt = self.build_prompt(subtask, context, iteration, max_iterations)
        
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}]
        )

        self.total_input_tokens += message.usage.input_tokens
        self.total_output_tokens += message.usage.output_tokens
        # "max_tokens" here means the subtask's output was cut off
        self.last_stop_reason = message.stop_reason

        response = message.content[0].text

        print(f"Tokens: {message.usage.input_tokens} in, {message.usage.output_tokens} out (stop: {message.stop_reason})")
        
        return response
    
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
        """Save execution summary with costs"""
        summary_path = os.path.join(self.debug_dir, "execution_summary.json")
        
        input_cost = (self.total_input_tokens / 1_000_000) * self.input_price_per_million
        output_cost = (self.total_output_tokens / 1_000_000) * self.output_price_per_million
        total_cost = input_cost + output_cost
        
        summary = {
            "run_timestamp": datetime.now().isoformat(),
            "main_task": self.main_task,
            "num_subtasks_generated": len(self.subtasks),
            "total_iterations": len(set(e["iteration"] for e in self.execution_log)),
            "completed_subtasks": list(self.completed_subtasks),
            "execution_log": self.execution_log,
            "final_state": {
                "all_complete": len(self.completed_subtasks) == len(self.subtasks)
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
    
    def run(self, task_description: str, max_iterations: int = 5):
        """Main orchestration loop with automatic decomposition"""
        self.main_task = task_description
        
        print(f"\n{'='*60}")
        print("AUTOMATIC MULTI-AGENT ORCHESTRATION")
        print(f"{'='*60}\n")
        print(f"Task: {task_description}\n")
        
        # Step 1: Decompose task
        self.subtasks = self.decompose_task(task_description)
        
        if not self.subtasks:
            print("Error: No subtasks generated")
            return
        
        # Step 2: Execute subtasks with coordination
        print(f"\n{'='*60}")
        print("EXECUTING SUBTASKS")
        print(f"{'='*60}\n")
        
        for iteration in range(max_iterations):
            print(f"\n{'='*60}")
            print(f"ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'='*60}\n")
            
            all_complete = True
            
            for subtask in self.subtasks:
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
                    self.log_execution_event(iteration, subtask_id, "COMPLETE", f"stop_reason={self.last_stop_reason}")
                elif self.is_blocked(response):
                    print(f"⧗ Subtask {subtask_id} is BLOCKED")
                    self.log_execution_event(iteration, subtask_id, "BLOCKED", f"stop_reason={self.last_stop_reason}")
                else:
                    print(f"→ Subtask {subtask_id} in progress")
                    self.log_execution_event(iteration, subtask_id, "IN_PROGRESS", f"stop_reason={self.last_stop_reason}")
            
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
        
        print(f"\n{'='*60}")
        print("COST SUMMARY")
        print(f"{'='*60}")
        print(f"Subtasks Generated:  {len(self.subtasks)}")
        print(f"Total Input Tokens:  {self.total_input_tokens:,}")
        print(f"Total Output Tokens: {self.total_output_tokens:,}")
        print(f"Total Tokens:        {self.total_input_tokens + self.total_output_tokens:,}")
        print(f"")
        print(f"Input Cost:          ${input_cost:.4f}")
        print(f"Output Cost:         ${output_cost:.4f}")
        print(f"Total Cost:          ${total_cost:.4f}")
        print(f"{'='*60}")
        print(f"\nResults saved to {self.output_dir}")


if __name__ == "__main__":
    # Example usage
    orchestrator = AutoDecomposingOrchestrator(clean_start=True)
    
    # Complex task that should benefit from decomposition
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
    
    orchestrator.run(task, max_iterations=8)
