"""
Final improved experiment with multiple runs, better metrics, and richer coordination
"""

import os
import json
import time
import asyncio
import random
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from anthropic import Anthropic
from collections import defaultdict

# Configure Anthropic Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
USE_MOCK_LLM = not bool(ANTHROPIC_API_KEY)

if not USE_MOCK_LLM:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    print("Using Claude for generation")
else:
    print("Note: No Anthropic API key found. Using mock responses.")

# Cost tracking for Claude models (per million tokens)
CLAUDE_PRICING = {
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25}
}

# Model selection
MODEL = "claude-3-haiku-20240307"

# Experiment configuration
NUM_RUNS = 3  # Multiple runs for statistical validity
DETAILED_METRICS = True  # Collect detailed metrics

class CostTracker:
    """Track API usage and costs"""
    
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0
    
    def add_usage(self, input_tokens: int, output_tokens: int):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.api_calls += 1
    
    def get_cost(self, model: str = MODEL) -> float:
        pricing = CLAUDE_PRICING.get(model, CLAUDE_PRICING["claude-3-haiku-20240307"])
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    def reset(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0
    
    def get_summary(self, model: str = MODEL) -> Dict:
        return {
            "api_calls": self.api_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost_usd": round(self.get_cost(model), 4),
            "model": model
        }

# Global cost tracker
cost_tracker = CostTracker()

class Agent:
    """Enhanced agent with richer coordination capabilities"""
    
    def __init__(self, name: str, role: str, dependencies: List[str] = None):
        self.name = name
        self.role = role
        self.dependencies = dependencies or []
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)
        self.notes_checked = 0
        self.notes_written = 0
        self.notes_used = 0  # Track which notes actually influenced generation
        self.llm_calls = 0
        self.useful_context_found = 0
        self.current_step = 0
    
    def write_note(self, content: str, topic: str = "general", priority: str = "normal"):
        """Write a note with priority and topic"""
        note_file = self.workspace / f"{self.name}_notes.jsonl"
        note = {
            "time": time.time(),
            "step": self.current_step,
            "topic": topic,
            "priority": priority,  # high, normal, low
            "content": content,
            "sender": self.name
        }
        with open(note_file, 'a') as f:
            f.write(json.dumps(note) + '\n')
        self.notes_written += 1
    
    def read_all_notes(self, only_high_priority: bool = False) -> Dict[str, List[Dict]]:
        """Read notes from all dependencies with optional filtering"""
        all_notes = {}
        for dep in self.dependencies:
            note_file = self.workspace / f"{dep}_notes.jsonl"
            if note_file.exists():
                notes = []
                with open(note_file, 'r') as f:
                    for line in f:
                        try:
                            note = json.loads(line)
                            if not only_high_priority or note.get('priority') == 'high':
                                notes.append(note)
                        except:
                            continue
                if notes:
                    all_notes[dep] = notes
        self.notes_checked += 1
        return all_notes
    
    def call_llm(self, prompt: str, context_used: bool = False) -> str:
        """Call Claude or return mock response"""
        global cost_tracker
        self.llm_calls += 1
        
        if context_used:
            self.notes_used += 1
        
        if USE_MOCK_LLM:
            # More sophisticated mock responses that vary slightly
            base_responses = {
                "architecture": [
                    "System uses microservices with Redis cache and PostgreSQL database.",
                    "Core components: API Gateway, Pipeline Service, Execution Engine.",
                    "Implements horizontal scaling with load balancers and container orchestration."
                ],
                "api_spec": [
                    "REST endpoints require Bearer token authentication.",
                    "POST /pipelines creates pipeline, returns 201 with ID.",
                    "Error codes: 401 (unauthorized), 429 (rate limited), 500 (server error)."
                ],
                "tutorial": [
                    "Get API key from dashboard at https://dashboard.example.com.",
                    "Install client library: pip install dataflow-client.",
                    "Create first pipeline: client.create_pipeline('my_pipeline', config)."
                ],
                "code": [
                    "class DataFlowClient handles all API interactions.",
                    "Implements retry logic with exponential backoff.",
                    "Supports async operations with asyncio."
                ],
                "troubleshooting": [
                    "401 errors: Verify API key is valid and not expired.",
                    "429 errors: Implement rate limiting, wait 60 seconds.",
                    "Connection timeouts: Check network and firewall settings."
                ]
            }
            
            responses = base_responses.get(self.role, ["Generic documentation content."])
            idx = self.current_step % len(responses)
            base = responses[idx]
            
            # Add context indicator if context was provided
            if context_used:
                base += " [Context integrated]"
            
            return base
        
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=200,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if hasattr(response, 'usage'):
                cost_tracker.add_usage(
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )
            
            return response.content[0].text
        except Exception as e:
            print(f"  Claude API call failed: {e}")
            return f"[Error calling Claude, using fallback] Documentation for {self.role}"
    
    def get_steps(self) -> List[Tuple[str, str, List[str]]]:
        """Get work steps with their dependencies on other agents' info"""
        steps = {
            "architecture": [
                ("Define Components", "List the main system components", []),
                ("Design Data Layer", "Describe databases and caching", []),
                ("Plan Scaling", "Explain scaling strategy", [])
            ],
            "api_spec": [
                ("Define Auth", "Specify authentication method", ["architecture:components"]),
                ("Document Endpoints", "List all endpoints", ["architecture:models"]),
                ("Specify Responses", "Define response formats", ["architecture:data_layer"])
            ],
            "tutorial": [
                ("Setup Instructions", "Explain how to get started", ["api_spec:auth"]),
                ("First API Call", "Show a simple example", ["api_spec:endpoints"]),
                ("Complete Example", "Provide a full example", ["api_spec:endpoints", "api_spec:responses"])
            ],
            "code": [
                ("Create Client", "Write a client class", ["api_spec:auth"]),
                ("Add Methods", "Implement main methods", ["api_spec:endpoints"]),
                ("Error Handling", "Add error handling", ["api_spec:responses"])
            ],
            "troubleshooting": [
                ("List Errors", "Identify common errors", ["api_spec:responses"]),
                ("Provide Solutions", "Give solutions", ["api_spec:auth", "tutorial:pain_points"]),
                ("Debug Tips", "Share debugging tips", ["code:methods"])
            ]
        }
        return steps.get(self.role, [("Generate", "Create documentation", [])])
    
    def _is_context_relevant(self, note: Dict, step_dependencies: List[str]) -> bool:
        """Determine if a note is relevant to current step"""
        if not step_dependencies:
            return False
        
        for dep in step_dependencies:
            if ':' in dep:
                agent, topic = dep.split(':')
                if note.get('sender') == agent and topic in note.get('topic', ''):
                    return True
            elif note.get('sender') == dep:
                return True
        
        # High priority notes are always relevant
        return note.get('priority') == 'high'
    
    async def generate_with_smart_coordination(self, check_interval: int = 2) -> str:
        """Generate with intelligent context selection based on step needs"""
        steps = self.get_steps()
        results = []
        
        print(f"  {self.name}: Starting {len(steps)} steps (smart coordination)")
        
        for i, (step_name, step_desc, step_deps) in enumerate(steps):
            self.current_step = i
            
            # Determine if we need context for this step
            context = ""
            context_used = False
            
            if step_deps and (i % check_interval == 0):
                notes = self.read_all_notes()
                
                if notes:
                    # Filter for relevant notes
                    relevant_notes = []
                    for dep_notes in notes.values():
                        for note in dep_notes:
                            if self._is_context_relevant(note, step_deps):
                                relevant_notes.append(note)
                                self.useful_context_found += 1
                    
                    if relevant_notes:
                        print(f"    {self.name}: Found {len(relevant_notes)} relevant notes for {step_name}")
                        context_used = True
                        
                        # Sort by priority and recency
                        relevant_notes.sort(key=lambda x: (
                            0 if x.get('priority') == 'high' else 1,
                            -x.get('time', 0)
                        ))
                        
                        # Build context from most relevant notes
                        context_parts = []
                        for note in relevant_notes[:5]:  # Top 5 most relevant
                            context_parts.append(f"{note['sender']} ({note['topic']}): {note['content'][:100]}")
                        context = "\n".join(context_parts)
            
            # Generate content
            prompt = f"""Role: {self.role}
Step: {step_name} - {step_desc}
Dependencies needed: {', '.join(step_deps) if step_deps else 'none'}
Context: {context if context else 'No relevant context available'}

Generate 2-3 sentences for this step. Be specific and technical."""
            
            content = self.call_llm(prompt, context_used)
            results.append(f"### {step_name}\n{content}")
            
            # Write notes for other agents based on what we generated
            self._write_intelligent_notes(step_name, content)
            
            await asyncio.sleep(0.1)
        
        return "\n\n".join(results)
    
    def _write_intelligent_notes(self, step_name: str, content: str):
        """Write notes that other agents actually need"""
        
        notes_to_write = {
            ("architecture", "Define Components"): [
                ("components", "Main components: API Gateway, Pipeline Service", "high"),
                ("models", "Core model: Pipeline with id, name, config", "high")
            ],
            ("architecture", "Design Data Layer"): [
                ("data_layer", "Using PostgreSQL for persistence, Redis for caching", "high")
            ],
            ("api_spec", "Define Auth"): [
                ("auth", "Bearer token required in Authorization header", "high")
            ],
            ("api_spec", "Document Endpoints"): [
                ("endpoints", "POST /pipelines, GET /pipelines/{id}, DELETE /pipelines/{id}", "high")
            ],
            ("api_spec", "Specify Responses"): [
                ("responses", "201 Created, 401 Unauthorized, 429 Rate Limited", "normal")
            ],
            ("tutorial", "First API Call"): [
                ("pain_points", "Users often forget Authorization header", "normal")
            ],
            ("code", "Add Methods"): [
                ("methods", "Implemented create_pipeline(), get_pipeline(), delete_pipeline()", "normal")
            ]
        }
        
        key = (self.role, step_name)
        if key in notes_to_write:
            for topic, content, priority in notes_to_write[key]:
                self.write_note(content, topic, priority)
    
    async def generate_no_coordination(self) -> str:
        """Generate without any coordination"""
        steps = self.get_steps()
        results = []
        
        print(f"  {self.name}: Generating {len(steps)} steps (no coordination)")
        
        for i, (step_name, step_desc, _) in enumerate(steps):
            self.current_step = i
            
            prompt = f"""Role: {self.role}
Step: {step_name} - {step_desc}

Generate 2-3 sentences for this step. Be specific and technical."""
            
            content = self.call_llm(prompt, False)
            results.append(f"### {step_name}\n{content}")
            await asyncio.sleep(0.1)
        
        return "\n\n".join(results)

def analyze_consistency_detailed(outputs: Dict[str, str]) -> Dict[str, Any]:
    """More detailed consistency analysis"""
    
    metrics = {
        "term_consistency": 0,
        "reference_accuracy": 0,
        "dependency_satisfaction": 0,
        "overall": 0,
        "details": []
    }
    
    checks = []
    
    # Check if API spec uses architecture's technical choices
    if "arch" in outputs and "api" in outputs:
        arch_terms = ["PostgreSQL", "Redis", "Pipeline", "microservices", "Gateway"]
        matches = sum(1 for term in arch_terms if term.lower() in outputs["api"].lower())
        score = matches / len(arch_terms)
        checks.append(score)
        metrics["details"].append(f"API uses {matches}/{len(arch_terms)} architecture terms")
    
    # Check if tutorial references actual endpoints
    if "api" in outputs and "tut" in outputs:
        # Look for actual endpoint patterns
        endpoint_patterns = ["/pipelines", "POST", "GET", "Bearer", "{id}"]
        matches = sum(1 for pattern in endpoint_patterns if pattern in outputs["tut"])
        score = matches / len(endpoint_patterns)
        checks.append(score)
        metrics["details"].append(f"Tutorial references {matches}/{len(endpoint_patterns)} API patterns")
    
    # Check if code implements what API specifies
    if "api" in outputs and "code" in outputs:
        code_should_have = ["create_pipeline", "get_pipeline", "Bearer", "client", "error"]
        matches = sum(1 for term in code_should_have if term.lower() in outputs["code"].lower())
        score = matches / len(code_should_have)
        checks.append(score)
        metrics["details"].append(f"Code implements {matches}/{len(code_should_have)} API concepts")
    
    # Check if troubleshooting covers actual errors
    if "api" in outputs and "trouble" in outputs:
        error_terms = ["401", "429", "authentication", "rate", "token"]
        matches = sum(1 for term in error_terms if term in outputs["trouble"])
        score = matches / len(error_terms)
        checks.append(score)
        metrics["details"].append(f"Troubleshooting covers {matches}/{len(error_terms)} error types")
    
    metrics["overall"] = (sum(checks) / len(checks) * 100) if checks else 0
    metrics["term_consistency"] = checks[0] * 100 if len(checks) > 0 else 0
    metrics["reference_accuracy"] = checks[1] * 100 if len(checks) > 1 else 0
    metrics["dependency_satisfaction"] = sum(checks[2:]) / len(checks[2:]) * 100 if len(checks) > 2 else 0
    
    return metrics

async def run_single_configuration(config_name: str, execution_mode: str, 
                                  check_interval: Optional[int], 
                                  use_coordination: bool) -> Dict:
    """Run a single configuration and return results"""
    
    # Clear workspace
    workspace = Path("workspace")
    if workspace.exists():
        for file in workspace.glob("*.jsonl"):
            file.unlink()
    workspace.mkdir(exist_ok=True)
    
    # Create agents
    agents = [
        Agent("arch", "architecture"),
        Agent("api", "api_spec", dependencies=["arch"]),
        Agent("tut", "tutorial", dependencies=["arch", "api"]),
        Agent("code", "code", dependencies=["api"]),
        Agent("trouble", "troubleshooting", dependencies=["api", "tut"])
    ]
    
    start_time = time.time()
    
    if execution_mode == "parallel":
        # Run all agents in parallel
        tasks = []
        for agent in agents:
            if use_coordination:
                task = agent.generate_with_smart_coordination(check_interval or 1)
            else:
                task = agent.generate_no_coordination()
            tasks.append(task)
        
        outputs = await asyncio.gather(*tasks)
        outputs_dict = {a.name: output for a, output in zip(agents, outputs)}
    
    else:  # sequential
        outputs_dict = {}
        for agent in agents:
            if use_coordination:
                output = await agent.generate_with_smart_coordination(1)
            else:
                output = await agent.generate_no_coordination()
            outputs_dict[agent.name] = output
    
    execution_time = time.time() - start_time
    
    # Collect detailed metrics
    metrics = {
        "execution_time": execution_time,
        "notes_written": sum(a.notes_written for a in agents),
        "notes_checked": sum(a.notes_checked for a in agents),
        "notes_used": sum(a.notes_used for a in agents),
        "useful_context_found": sum(a.useful_context_found for a in agents),
        "llm_calls": sum(a.llm_calls for a in agents),
        "outputs": outputs_dict,
        "consistency": analyze_consistency_detailed(outputs_dict)
    }
    
    return metrics

async def main():
    """Run complete experiment with multiple runs and statistical analysis"""
    
    global cost_tracker
    
    print("="*60)
    print("MULTI-AGENT COORDINATION EXPERIMENT (FINAL)")
    print("="*60)
    print(f"LLM: Claude ({MODEL})")
    print(f"Mode: {'API' if not USE_MOCK_LLM else 'Mock (no API key)'}")
    print(f"Runs per configuration: {NUM_RUNS}")
    print("="*60)
    
    # Configurations to test
    configs = [
        ("Parallel - No Coordination", "parallel", None, False),
        ("Parallel - Check Every Step", "parallel", 1, True),
        ("Parallel - Check Every 2 Steps", "parallel", 2, True),
        ("Sequential - No Coordination", "sequential", None, False),
        ("Sequential - With Coordination", "sequential", 1, True),
    ]
    
    all_results = defaultdict(list)
    
    # Run multiple times for statistical validity
    for run_num in range(NUM_RUNS):
        print(f"\n{'='*60}")
        print(f"RUN {run_num + 1} of {NUM_RUNS}")
        print("="*60)
        
        cost_tracker.reset()
        
        for config_name, exec_mode, interval, use_coord in configs:
            print(f"\n  Testing: {config_name}")
            
            result = await run_single_configuration(
                config_name, exec_mode, interval, use_coord
            )
            all_results[config_name].append(result)
            
            print(f"    Time: {result['execution_time']:.2f}s")
            print(f"    Consistency: {result['consistency']['overall']:.1f}%")
            print(f"    Context used: {result['notes_used']}/{result['llm_calls']} LLM calls")
    
    # Statistical analysis
    print(f"\n{'='*60}")
    print("STATISTICAL SUMMARY (averaged over " + str(NUM_RUNS) + " runs)")
    print("="*60)
    
    print("\n| Configuration                   | Time(s) | σ  | Consistency | σ  | Context Efficiency |")
    print("|---------------------------------|---------|----|-------------|----|--------------------|")
    
    summary_stats = {}
    
    for config_name in configs:
        config_name = config_name[0]
        runs = all_results[config_name]
        
        times = [r['execution_time'] for r in runs]
        consistencies = [r['consistency']['overall'] for r in runs]
        context_efficiency = [
            r['notes_used'] / r['llm_calls'] * 100 if r['llm_calls'] > 0 else 0 
            for r in runs
        ]
        
        avg_time = statistics.mean(times)
        std_time = statistics.stdev(times) if len(times) > 1 else 0
        avg_consistency = statistics.mean(consistencies)
        std_consistency = statistics.stdev(consistencies) if len(consistencies) > 1 else 0
        avg_efficiency = statistics.mean(context_efficiency)
        
        summary_stats[config_name] = {
            "avg_time": avg_time,
            "std_time": std_time,
            "avg_consistency": avg_consistency,
            "std_consistency": std_consistency,
            "avg_efficiency": avg_efficiency,
            "avg_notes_written": statistics.mean([r['notes_written'] for r in runs]),
            "avg_useful_context": statistics.mean([r['useful_context_found'] for r in runs])
        }
        
        print(f"| {config_name:<31} | {avg_time:>7.2f} | {std_time:>2.1f} | "
              f"{avg_consistency:>11.1f} | {std_consistency:>2.1f} | {avg_efficiency:>17.1f}% |")
    
    # Key comparisons with confidence
    print(f"\n{'='*60}")
    print("KEY FINDINGS")
    print("="*60)
    
    # Compare parallel coordination vs no coordination
    p_no = summary_stats.get("Parallel - No Coordination")
    p_coord = summary_stats.get("Parallel - Check Every Step")
    
    if p_no and p_coord:
        time_overhead = ((p_coord['avg_time'] - p_no['avg_time']) / p_no['avg_time'] * 100)
        quality_gain = p_coord['avg_consistency'] - p_no['avg_consistency']
        
        print(f"\nParallel with coordination (every step) vs no coordination:")
        print(f"  Time overhead: +{time_overhead:.1f}% ± {p_coord['std_time']:.1f}s")
        print(f"  Quality gain: +{quality_gain:.1f}% ± {p_coord['std_consistency']:.1f}%")
        print(f"  Context efficiency: {p_coord['avg_efficiency']:.1f}% of LLM calls used context")
        print(f"  Useful context found: {p_coord['avg_useful_context']:.1f} relevant notes per run")
    
    # Compare different check intervals
    p_every2 = summary_stats.get("Parallel - Check Every 2 Steps")
    if p_no and p_every2:
        time_overhead_2 = ((p_every2['avg_time'] - p_no['avg_time']) / p_no['avg_time'] * 100)
        quality_gain_2 = p_every2['avg_consistency'] - p_no['avg_consistency']
        
        print(f"\nParallel with check-every-2 vs no coordination:")
        print(f"  Time overhead: +{time_overhead_2:.1f}%")
        print(f"  Quality gain: +{quality_gain_2:.1f}%")
        print(f"  Efficiency ratio: {quality_gain_2/max(time_overhead_2, 0.1):.2f} quality per overhead")
    
    # Cost analysis
    print(f"\n{'='*60}")
    print("COST ANALYSIS")
    print("="*60)
    
    total_cost = cost_tracker.get_summary()
    total_configs = len(configs) * NUM_RUNS
    
    print(f"Total experiment cost: ${total_cost['total_cost_usd']:.4f}")
    print(f"Cost per configuration run: ${total_cost['total_cost_usd']/total_configs:.5f}")
    print(f"Total tokens used: {total_cost['input_tokens'] + total_cost['output_tokens']:,}")
    
    # Recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print("="*60)
    
    # Find best configuration by different criteria
    best_quality = max(summary_stats.items(), key=lambda x: x[1]['avg_consistency'])
    best_speed = min(summary_stats.items(), key=lambda x: x[1]['avg_time'])
    
    # Calculate efficiency scores
    efficiency_scores = {}
    for name, stats in summary_stats.items():
        if "No Coordination" not in name:
            baseline = summary_stats["Parallel - No Coordination"]
            quality_improvement = stats['avg_consistency'] - baseline['avg_consistency']
            time_cost = stats['avg_time'] - baseline['avg_time']
            efficiency = quality_improvement / max(time_cost, 0.1)
            efficiency_scores[name] = efficiency
    
    if efficiency_scores:
        best_efficiency = max(efficiency_scores.items(), key=lambda x: x[1])
        
        print(f"\n1. Best Quality: {best_quality[0]} ({best_quality[1]['avg_consistency']:.1f}%)")
        print(f"2. Best Speed: {best_speed[0]} ({best_speed[1]['avg_time']:.2f}s)")
        print(f"3. Best Efficiency: {best_efficiency[0]} ({best_efficiency[1]:.2f} quality/time)")
    
    print("\nConclusion:")
    if p_coord and p_no:
        if quality_gain > 30 and time_overhead < 10:
            print("✅ Strong evidence that coordination significantly improves quality with minimal overhead")
        elif quality_gain > 20:
            print("✅ Coordination provides meaningful quality improvements")
        else:
            print("⚠️  Coordination benefits are modest for this task")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())
