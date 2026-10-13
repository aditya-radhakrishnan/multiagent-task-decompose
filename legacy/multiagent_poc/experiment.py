"""
Ready-to-run POC with configurable periodic coordination
Test how often agents should check for updates from each other
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from anthropic import Anthropic

# Configure Anthropic Claude (set your key or use mock)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
USE_MOCK_LLM = not bool(ANTHROPIC_API_KEY)  # Use mock if no API key

if not USE_MOCK_LLM:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    print("Using Claude for generation")
else:
    print("Note: No Anthropic API key found. Using mock responses.")

class Agent:
    """Agent that can work in steps and check for coordination files periodically"""
    
    def __init__(self, name: str, role: str, dependencies: List[str] = None):
        self.name = name
        self.role = role
        self.dependencies = dependencies or []
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)
        self.notes_checked = 0
        self.notes_written = 0
        self.llm_calls = 0
    
    def write_note(self, content: str, topic: str = "general"):
        """Write a note that other agents can read"""
        note_file = self.workspace / f"{self.name}_notes.jsonl"
        note = {
            "time": time.time(),
            "step": self.current_step if hasattr(self, 'current_step') else 0,
            "topic": topic,
            "content": content
        }
        with open(note_file, 'a') as f:
            f.write(json.dumps(note) + '\n')
        self.notes_written += 1
    
    def read_all_notes(self) -> Dict[str, List[Dict]]:
        """Read notes from all dependencies"""
        all_notes = {}
        for dep in self.dependencies:
            note_file = self.workspace / f"{dep}_notes.jsonl"
            if note_file.exists():
                notes = []
                with open(note_file, 'r') as f:
                    for line in f:
                        try:
                            notes.append(json.loads(line))
                        except:
                            continue
                if notes:
                    all_notes[dep] = notes
        self.notes_checked += 1
        return all_notes
    
    def call_llm(self, prompt: str) -> str:
        """Call Claude or return mock response"""
        self.llm_calls += 1
        
        if USE_MOCK_LLM:
            # Generate mock content that's somewhat relevant
            mock_responses = {
                "architecture": f"System uses microservices with Redis cache and PostgreSQL. Main components: API Gateway, Pipeline Service, Execution Engine.",
                "api_spec": f"REST endpoints require Bearer token. POST /pipelines creates new pipeline. Returns 201 with pipeline ID. Errors: 401 unauthorized, 429 rate limited.",
                "tutorial": f"First, get your API key from dashboard. Install client: pip install dataflow. Create pipeline: client.create_pipeline('my_pipeline').",
                "code": f"class DataFlowClient: def __init__(self, api_key): self.key = api_key. def create_pipeline(self, name): return requests.post('/pipelines', ...).",
                "troubleshooting": f"Common error: 401 - Check API key. 429 - You're rate limited, wait 60s. Connection timeout - Check network."
            }
            
            base_response = mock_responses.get(self.role, "Generated documentation content.")
            return f"{base_response} [Step {self.current_step if hasattr(self, 'current_step') else 0}]"
        
        try:
            # Use Claude API
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cheap for testing
                max_tokens=200,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"  Claude API call failed: {e}")
            return f"[Error calling Claude, using fallback] Documentation for {self.role}"
    
    def get_steps(self) -> List[Tuple[str, str]]:
        """Get the work steps for this agent's role"""
        steps = {
            "architecture": [
                ("Define Components", "List the main system components and their purposes"),
                ("Design Data Layer", "Describe databases, caching, and data flow"),
                ("Plan Scaling", "Explain how the system scales horizontally and vertically")
            ],
            "api_spec": [
                ("Define Auth", "Specify authentication method and requirements"),
                ("Document Endpoints", "List all endpoints with methods and paths"),
                ("Specify Responses", "Define response formats and status codes")
            ],
            "tutorial": [
                ("Setup Instructions", "Explain how to get started with API access"),
                ("First API Call", "Show a simple example of calling the API"),
                ("Complete Example", "Provide a full working example")
            ],
            "code": [
                ("Create Client", "Write a client class for the API"),
                ("Add Methods", "Implement methods for main endpoints"),
                ("Error Handling", "Add proper error handling and retries")
            ],
            "troubleshooting": [
                ("List Errors", "Identify common error codes and their meanings"),
                ("Provide Solutions", "Give solutions for each error"),
                ("Debug Tips", "Share debugging techniques and tools")
            ]
        }
        return steps.get(self.role, [("Generate", "Create documentation")])
    
    async def generate_with_periodic_checks(self, check_interval: int = 2) -> str:
        """
        Generate content step by step, checking for updates every N steps
        
        Args:
            check_interval: How many steps between checking for notes (1 = every step)
        """
        steps = self.get_steps()
        results = []
        accumulated_context = ""
        
        print(f"  {self.name}: Starting {len(steps)} steps (checking every {check_interval} steps)")
        
        for i, (step_name, step_description) in enumerate(steps):
            self.current_step = i
            
            # Check for updates based on interval
            if i % check_interval == 0:
                notes = self.read_all_notes()
                if notes:
                    print(f"  {self.name}: [Step {i+1}] Checking notes... found {sum(len(n) for n in notes.values())} total")
                    
                    # Build context from notes
                    context_parts = []
                    for dep, dep_notes in notes.items():
                        # Use most recent 3 notes from each dependency
                        recent = dep_notes[-3:]
                        for note in recent:
                            context_parts.append(f"{dep}: {note['content'][:100]}")
                    
                    accumulated_context = "\n".join(context_parts)
            
            # Generate content for this step
            prompt = f"""Role: {self.role}
Step: {step_name} - {step_description}
Context from other agents: {accumulated_context if accumulated_context else 'No context yet'}

Generate 2-3 sentences for this step."""
            
            content = self.call_llm(prompt)
            results.append(f"### {step_name}\n{content}")
            
            # Write notes about what we learned/created
            if self.role == "architecture" and i == 0:  # After components
                self.write_note("Using PostgreSQL and Redis", "infrastructure")
                self.write_note("Main model: Pipeline with id, name, config", "models")
            elif self.role == "api_spec" and i == 1:  # After endpoints
                self.write_note("POST /pipelines, GET /pipelines/{id}", "endpoints")
                self.write_note("Auth: Bearer token required", "auth")
            elif self.role == "tutorial" and i == 1:  # After first call
                self.write_note("Users struggle with auth setup", "pain_points")
            
            # Small delay to simulate work
            await asyncio.sleep(0.1)
        
        return "\n\n".join(results)
    
    async def generate_no_coordination(self) -> str:
        """Generate all content without checking for notes"""
        steps = self.get_steps()
        results = []
        
        print(f"  {self.name}: Generating {len(steps)} steps (no coordination)")
        
        for i, (step_name, step_description) in enumerate(steps):
            self.current_step = i
            
            prompt = f"""Role: {self.role}
Step: {step_name} - {step_description}

Generate 2-3 sentences for this step."""
            
            content = self.call_llm(prompt)
            results.append(f"### {step_name}\n{content}")
            await asyncio.sleep(0.1)
        
        return "\n\n".join(results)

async def run_experiment(check_interval: int = 2, use_coordination: bool = True):
    """
    Run the experiment with configurable check interval
    
    Args:
        check_interval: How often to check for notes (1 = every step, 2 = every other step, etc.)
        use_coordination: If False, run without any coordination (baseline)
    """
    
    # Clear workspace
    workspace = Path("workspace")
    if workspace.exists():
        for file in workspace.glob("*.jsonl"):
            file.unlink()
    workspace.mkdir(exist_ok=True)
    
    # Create agents with dependencies
    agents = [
        Agent("arch", "architecture"),
        Agent("api", "api_spec", dependencies=["arch"]),
        Agent("tut", "tutorial", dependencies=["arch", "api"]),
        Agent("code", "code", dependencies=["api"]),
        Agent("trouble", "troubleshooting", dependencies=["api", "tut"])
    ]
    
    print(f"\nRunning {'WITH' if use_coordination else 'WITHOUT'} coordination")
    if use_coordination:
        print(f"Check interval: every {check_interval} step(s)")
    print("-" * 50)
    
    start_time = time.time()
    
    # Run all agents in parallel
    tasks = []
    for agent in agents:
        if use_coordination:
            task = agent.generate_with_periodic_checks(check_interval)
        else:
            task = agent.generate_no_coordination()
        tasks.append(task)
    
    outputs = await asyncio.gather(*tasks)
    
    execution_time = time.time() - start_time
    
    # Collect metrics
    total_notes_written = sum(a.notes_written for a in agents)
    total_notes_checked = sum(a.notes_checked for a in agents)
    total_llm_calls = sum(a.llm_calls for a in agents)
    
    # Save outputs
    for agent, output in zip(agents, outputs):
        output_file = workspace / f"output_{agent.name}.md"
        with open(output_file, 'w') as f:
            f.write(f"# {agent.role.title()} Documentation\n\n")
            f.write(output)
    
    return {
        "execution_time": execution_time,
        "notes_written": total_notes_written,
        "notes_checked": total_notes_checked,
        "llm_calls": total_llm_calls,
        "outputs": {a.name: output for a, output in zip(agents, outputs)}
    }

def analyze_consistency(outputs: Dict[str, str]) -> float:
    """Simple metric: check if dependent agents mention things from their dependencies"""
    
    consistency_checks = []
    
    # Check if API spec mentions architecture terms
    if "arch" in outputs and "api" in outputs:
        arch_terms = ["PostgreSQL", "Redis", "microservice", "Pipeline"]
        matches = sum(1 for term in arch_terms if term.lower() in outputs["api"].lower())
        consistency_checks.append(matches / len(arch_terms))
    
    # Check if tutorial mentions API endpoints
    if "api" in outputs and "tut" in outputs:
        api_terms = ["/pipelines", "Bearer", "POST", "GET"]
        matches = sum(1 for term in api_terms if term in outputs["tut"])
        consistency_checks.append(matches / len(api_terms))
    
    # Check if troubleshooting mentions errors from API spec
    if "api" in outputs and "trouble" in outputs:
        error_terms = ["401", "429", "authentication", "rate"]
        matches = sum(1 for term in error_terms if term in outputs["trouble"])
        consistency_checks.append(matches / len(error_terms))
    
    return (sum(consistency_checks) / len(consistency_checks) * 100) if consistency_checks else 0

async def main():
    """Compare different check intervals to find the optimal frequency"""
    
    print("="*60)
    print("PERIODIC COORDINATION EXPERIMENT")
    print("="*60)
    print(f"LLM Mode: {'Claude API' if not USE_MOCK_LLM else 'Mock (no API key)'}")
    
    # Test different configurations
    configs = [
        ("No Coordination", None),  # Baseline
        ("Check Every Step", 1),    # Maximum coordination
        ("Check Every 2 Steps", 2), # Balanced
        ("Check Every 3 Steps", 3), # Minimal coordination
    ]
    
    results = {}
    
    for config_name, interval in configs:
        print(f"\n{'='*60}")
        print(f"Testing: {config_name}")
        print("="*60)
        
        if interval is None:
            result = await run_experiment(use_coordination=False)
        else:
            result = await run_experiment(check_interval=interval, use_coordination=True)
        
        results[config_name] = result
        
        # Quick metrics
        print(f"\nMetrics:")
        print(f"  Time: {result['execution_time']:.2f}s")
        print(f"  Notes written: {result['notes_written']}")
        print(f"  Notes checked: {result['notes_checked']}")
        print(f"  LLM calls: {result['llm_calls']}")
        print(f"  Consistency: {analyze_consistency(result['outputs']):.1f}%")
    
    # Summary comparison
    print(f"\n{'='*60}")
    print("SUMMARY COMPARISON")
    print("="*60)
    
    print("\n| Configuration      | Time(s) | Notes Written | Notes Checked | LLM Calls | Consistency |")
    print("|-------------------|---------|---------------|---------------|-----------|-------------|")
    
    for config_name, result in results.items():
        consistency = analyze_consistency(result['outputs'])
        print(f"| {config_name:<17} | {result['execution_time']:>7.2f} | {result['notes_written']:>13} | "
              f"{result['notes_checked']:>13} | {result['llm_calls']:>9} | {consistency:>10.1f}% |")
    
    # Key insights
    print(f"\n{'='*60}")
    print("KEY FINDINGS")
    print("="*60)
    
    no_coord = results["No Coordination"]
    every_step = results.get("Check Every Step", no_coord)
    every_2 = results.get("Check Every 2 Steps", no_coord)
    
    if "Check Every Step" in results:
        overhead_1 = ((every_step['execution_time'] - no_coord['execution_time']) / no_coord['execution_time'] * 100)
        quality_1 = analyze_consistency(every_step['outputs']) - analyze_consistency(no_coord['outputs'])
        
        print(f"\nChecking every step:")
        print(f"  - Overhead: +{overhead_1:.1f}% execution time")
        print(f"  - Quality gain: +{quality_1:.1f}% consistency")
    
    if "Check Every 2 Steps" in results:
        overhead_2 = ((every_2['execution_time'] - no_coord['execution_time']) / no_coord['execution_time'] * 100)
        quality_2 = analyze_consistency(every_2['outputs']) - analyze_consistency(no_coord['outputs'])
        
        print(f"\nChecking every 2 steps:")
        print(f"  - Overhead: +{overhead_2:.1f}% execution time")
        print(f"  - Quality gain: +{quality_2:.1f}% consistency")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())
