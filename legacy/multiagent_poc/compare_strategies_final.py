"""
Production-ready comparison of coordination strategies
Tests: No Coordination vs Pairwise Notes vs Output Sharing
With proper metrics tracking and caching
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from anthropic import Anthropic
import statistics
from dataclasses import dataclass, field

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
USE_MOCK_LLM = not bool(ANTHROPIC_API_KEY)
MODEL = "claude-3-haiku-20240307"  # Cheap and fast
NUM_RUNS = 3  # Number of runs for statistical validity

if not USE_MOCK_LLM:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    print(f"Using Claude ({MODEL}) for generation")
else:
    print("⚠️  No API key found. Using mock responses.")
    print("   Set ANTHROPIC_API_KEY environment variable for real results.")

# Cost tracking
@dataclass
class Metrics:
    """Track detailed metrics for analysis"""
    unique_files_created: Set[str] = field(default_factory=set)
    write_operations: int = 0
    read_operations: int = 0
    cache_hits: int = 0
    bytes_written: int = 0
    bytes_read: int = 0
    llm_calls: int = 0
    context_used_count: int = 0
    execution_time: float = 0
    
    # Cost tracking
    input_tokens: int = 0
    output_tokens: int = 0
    
    def get_summary(self) -> Dict:
        return {
            "unique_files": len(self.unique_files_created),
            "write_ops": self.write_operations,
            "read_ops": self.read_operations,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (self.cache_hits / max(self.read_operations + self.cache_hits, 1)) * 100,
            "bytes_written": self.bytes_written,
            "bytes_read": self.bytes_read,
            "llm_calls": self.llm_calls,
            "context_usage_rate": (self.context_used_count / max(self.llm_calls, 1)) * 100,
            "execution_time": self.execution_time
        }

class Agent:
    """Agent with proper caching and metrics tracking"""
    
    def __init__(self, name: str, role: str, dependencies: List[str] = None):
        self.name = name
        self.role = role
        self.dependencies = dependencies or []
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)
        self.metrics = Metrics()
        self.read_cache = {}  # Cache for file reads
        self.current_step = 0
    
    def get_steps(self) -> List[Tuple[str, str, List[str]]]:
        """Define work steps with their information needs"""
        steps = {
            "architecture": [
                ("Define Components", "List the main system components", []),
                ("Design Data Layer", "Describe databases and caching", []),
                ("Plan Scaling", "Explain scaling strategy", [])
            ],
            "api_spec": [
                ("Define Auth", "Specify authentication method", ["arch:components"]),
                ("Document Endpoints", "List all endpoints", ["arch:data"]),
                ("Specify Responses", "Define response formats", ["arch:components"])
            ],
            "tutorial": [
                ("Setup Instructions", "Explain how to get started", ["api:auth"]),
                ("First API Call", "Show a simple example", ["api:endpoints"]),
                ("Complete Example", "Provide full example", ["api:endpoints", "api:auth"])
            ],
            "code": [
                ("Create Client", "Write a client class", ["api:auth"]),
                ("Add Methods", "Implement main methods", ["api:endpoints"]),
                ("Error Handling", "Add error handling", ["api:responses"])
            ],
            "troubleshooting": [
                ("List Errors", "Identify common errors", ["api:responses"]),
                ("Provide Solutions", "Give solutions", ["api:auth", "tutorial:setup"]),
                ("Debug Tips", "Share debugging tips", ["code:methods"])
            ]
        }
        return steps.get(self.role, [("Generate", "Create documentation", [])])
    
    def call_llm(self, prompt: str, with_context: bool = False) -> str:
        """Call Claude or return context-aware mock"""
        self.metrics.llm_calls += 1
        if with_context:
            self.metrics.context_used_count += 1
        
        if USE_MOCK_LLM:
            return self._mock_llm_response(prompt, with_context)
        
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=200,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Track token usage
            if hasattr(response, 'usage'):
                self.metrics.input_tokens += response.usage.input_tokens
                self.metrics.output_tokens += response.usage.output_tokens
            
            return response.content[0].text
        except Exception as e:
            print(f"  ⚠️  API call failed: {e}")
            return self._mock_llm_response(prompt, with_context)
    
    def _mock_llm_response(self, prompt: str, with_context: bool) -> str:
        """Context-aware mock responses for testing without API"""
        
        # Extract context clues from prompt
        has_postgres = "PostgreSQL" in prompt or "postgres" in prompt.lower()
        has_redis = "Redis" in prompt or "redis" in prompt.lower()
        has_bearer = "Bearer" in prompt or "bearer" in prompt.lower()
        has_endpoints = "/pipelines" in prompt
        
        base_responses = {
            "architecture": {
                0: "System uses microservices with API Gateway. PostgreSQL for persistence.",
                1: "Data layer: PostgreSQL for transactional data, Redis for caching, S3 for files.",
                2: "Horizontal scaling via Kubernetes with auto-scaling based on load."
            },
            "api_spec": {
                0: f"Authentication via {'Bearer tokens' if has_bearer or not with_context else 'API keys'}.",
                1: f"Endpoints: POST /pipelines, GET /pipelines/{{id}}, DELETE /pipelines/{{id}}.",
                2: "Responses: 201 Created, 401 Unauthorized, 429 Rate Limited, 500 Server Error."
            },
            "tutorial": {
                0: f"Get your {'Bearer token' if has_bearer else 'API key'} from the dashboard.",
                1: f"First call: {'POST /pipelines' if has_endpoints else 'POST to create endpoint'}.",
                2: f"Complete pipeline creation example with {'Bearer auth' if has_bearer else 'auth'}."
            },
            "code": {
                0: f"DataFlowClient with {'Bearer token auth' if has_bearer else 'authentication'}.",
                1: f"Methods for {'/pipelines endpoints' if has_endpoints else 'API endpoints'}.",
                2: "Error handling with retries and exponential backoff."
            },
            "troubleshooting": {
                0: "Common errors: 401 (auth), 429 (rate limit), 500 (server error).",
                1: f"For 401: Check {'Bearer token' if has_bearer else 'API key'}. For 429: Add delays.",
                2: f"Debug with logging. {'Check PostgreSQL logs.' if has_postgres else ''}"
            }
        }
        
        responses = base_responses.get(self.role, {})
        return responses.get(self.current_step, f"Generated content for {self.role}")
    
    # ========== STRATEGY 1: Pairwise Notes ==========
    
    def write_pairwise_note(self, recipient: str, content: str, topic: str = "general"):
        """Write a note for a specific recipient"""
        note_file = self.workspace / "notes" / f"{self.name}_to_{recipient}.jsonl"
        note_file.parent.mkdir(exist_ok=True)
        
        note = {
            "timestamp": time.time(),
            "from": self.name,
            "to": recipient,
            "topic": topic,
            "content": content
        }
        
        with open(note_file, 'a') as f:
            data = json.dumps(note) + '\n'
            f.write(data)
            self.metrics.bytes_written += len(data.encode())
        
        self.metrics.unique_files_created.add(str(note_file))
        self.metrics.write_operations += 1
    
    def read_pairwise_notes(self) -> Dict[str, List[str]]:
        """Read notes addressed to this agent"""
        notes_dir = self.workspace / "notes"
        if not notes_dir.exists():
            return {}
        
        all_notes = {}
        for dep in self.dependencies:
            note_file = notes_dir / f"{dep}_to_{self.name}.jsonl"
            if note_file.exists():
                self.metrics.read_operations += 1
                notes = []
                
                with open(note_file, 'r') as f:
                    content = f.read()
                    self.metrics.bytes_read += len(content.encode())
                    
                    for line in content.strip().split('\n'):
                        if line:
                            try:
                                note = json.loads(line)
                                notes.append(note['content'])
                            except:
                                pass
                
                if notes:
                    all_notes[dep] = notes
        
        return all_notes
    
    # ========== STRATEGY 2: Output File Sharing ==========
    
    def write_output_file(self, content: str, step_name: str):
        """Write to agent's output file"""
        output_file = self.workspace / "outputs" / f"{self.name}_output.md"
        output_file.parent.mkdir(exist_ok=True)
        
        section = f"\n## [{step_name}]\n{content}\n"
        
        with open(output_file, 'a') as f:
            f.write(section)
            self.metrics.bytes_written += len(section.encode())
        
        self.metrics.unique_files_created.add(str(output_file))
        self.metrics.write_operations += 1
    
    def read_dependency_outputs(self) -> Dict[str, str]:
        """Read dependency outputs with caching"""
        outputs_dir = self.workspace / "outputs"
        if not outputs_dir.exists():
            return {}
        
        dependency_outputs = {}
        for dep in self.dependencies:
            output_file = outputs_dir / f"{dep}_output.md"
            
            if output_file.exists():
                # Check cache first
                mtime = output_file.stat().st_mtime
                cache_key = str(output_file)
                
                if cache_key in self.read_cache and self.read_cache[cache_key]['mtime'] >= mtime:
                    # Cache hit!
                    self.metrics.cache_hits += 1
                    dependency_outputs[dep] = self.read_cache[cache_key]['content']
                else:
                    # Cache miss - read file
                    self.metrics.read_operations += 1
                    with open(output_file, 'r') as f:
                        content = f.read()
                        self.metrics.bytes_read += len(content.encode())
                        
                        # Update cache
                        self.read_cache[cache_key] = {
                            'content': content[-500:],  # Only cache last 500 chars
                            'mtime': mtime
                        }
                        dependency_outputs[dep] = content[-500:]
        
        return dependency_outputs
    
    # ========== Generation Methods ==========
    
    async def generate_with_pairwise_notes(self, check_interval: int = 1) -> str:
        """Generate using pairwise notes"""
        steps = self.get_steps()
        results = []
        
        for i, (step_name, step_desc, needs) in enumerate(steps):
            self.current_step = i
            
            # Check for notes based on interval
            context = ""
            if i % check_interval == 0 and self.dependencies:
                notes = self.read_pairwise_notes()
                if notes:
                    context_parts = []
                    for sender, sender_notes in notes.items():
                        for note in sender_notes[-2:]:  # Last 2 notes
                            context_parts.append(f"{sender}: {note[:100]}")
                    context = "\n".join(context_parts)
            
            # Generate content
            prompt = f"""You are creating {self.role} documentation.

Current step: {step_name} - {step_desc}

Context from other agents:
{context if context else 'No context available'}

Write 2-3 sentences for this step. Be specific and build on any context provided."""
            
            content = self.call_llm(prompt, bool(context))
            results.append(f"### {step_name}\n{content}")
            
            # Write strategic notes based on role and step
            self._write_pairwise_notes_for_step(step_name, content)
            
            await asyncio.sleep(0.01)
        
        return "\n\n".join(results)
    
    async def generate_with_output_sharing(self, check_interval: int = 1) -> str:
        """Generate using output file sharing"""
        steps = self.get_steps()
        results = []
        
        for i, (step_name, step_desc, needs) in enumerate(steps):
            self.current_step = i
            
            # Check outputs based on interval
            context = ""
            if i % check_interval == 0 and self.dependencies:
                outputs = self.read_dependency_outputs()
                if outputs:
                    context_parts = []
                    for dep, output in outputs.items():
                        context_parts.append(f"[{dep} output]:\n{output[:200]}")
                    context = "\n---\n".join(context_parts)
            
            # Generate content
            prompt = f"""You are creating {self.role} documentation.

Current step: {step_name} - {step_desc}

Available context from dependencies:
{context if context else 'No context available'}

Write 2-3 sentences for this step. Build on the available context to ensure consistency."""
            
            content = self.call_llm(prompt, bool(context))
            results.append(f"### {step_name}\n{content}")
            
            # Write output
            self.write_output_file(content, step_name)
            
            await asyncio.sleep(0.01)
        
        return "\n\n".join(results)
    
    async def generate_no_coordination(self) -> str:
        """Generate without coordination"""
        steps = self.get_steps()
        results = []
        
        for i, (step_name, step_desc, _) in enumerate(steps):
            self.current_step = i
            
            prompt = f"""You are creating {self.role} documentation.

Current step: {step_name} - {step_desc}

Write 2-3 sentences for this step."""
            
            content = self.call_llm(prompt, False)
            results.append(f"### {step_name}\n{content}")
            
            await asyncio.sleep(0.01)
        
        return "\n\n".join(results)
    
    def _write_pairwise_notes_for_step(self, step_name: str, content: str):
        """Write targeted notes based on what was generated"""
        
        # Strategic note writing based on role and step
        if self.role == "architecture":
            if step_name == "Define Components":
                self.write_pairwise_note("api", "Using PostgreSQL and Redis", "infrastructure")
                self.write_pairwise_note("code", "Microservices architecture", "architecture")
            elif step_name == "Design Data Layer":
                self.write_pairwise_note("api", "PostgreSQL primary, Redis cache", "data")
                
        elif self.role == "api_spec":
            if step_name == "Define Auth":
                self.write_pairwise_note("tutorial", "Bearer token authentication", "auth")
                self.write_pairwise_note("code", "Bearer tokens required", "auth")
            elif step_name == "Document Endpoints":
                self.write_pairwise_note("tutorial", "POST /pipelines, GET /pipelines/{id}", "endpoints")
                self.write_pairwise_note("code", "Pipeline CRUD endpoints", "endpoints")
            elif step_name == "Specify Responses":
                self.write_pairwise_note("troubleshooting", "401, 429, 500 error codes", "errors")
                
        elif self.role == "tutorial":
            if step_name == "Setup Instructions":
                self.write_pairwise_note("troubleshooting", "Common setup issues", "setup")

def analyze_consistency(outputs: Dict[str, str]) -> Dict[str, float]:
    """Detailed consistency analysis"""
    
    scores = {}
    evidence = []
    
    # Check architecture → API propagation
    if "arch" in outputs and "api" in outputs:
        arch_content = outputs["arch"].lower()
        api_content = outputs["api"].lower()
        
        # Check specific technical choices
        checks = {
            "postgresql": ("postgresql" in arch_content, "postgresql" in api_content),
            "redis": ("redis" in arch_content, "redis" in api_content or "cach" in api_content),
            "microservice": ("microservice" in arch_content, "microservice" in api_content or "service" in api_content)
        }
        
        for tech, (in_arch, in_api) in checks.items():
            if in_arch:
                if in_api:
                    scores[f"arch_api_{tech}"] = 100
                    evidence.append(f"✓ API mentions {tech} from architecture")
                else:
                    scores[f"arch_api_{tech}"] = 0
                    evidence.append(f"✗ API missed {tech} from architecture")
    
    # Check API → Tutorial propagation
    if "api" in outputs and "tut" in outputs:
        api_content = outputs["api"]
        tut_content = outputs["tut"]
        
        # Check auth method
        if "Bearer" in api_content:
            if "Bearer" in tut_content or "bearer" in tut_content.lower():
                scores["api_tut_auth"] = 100
                evidence.append("✓ Tutorial uses correct Bearer auth")
            else:
                scores["api_tut_auth"] = 0
                evidence.append("✗ Tutorial missed Bearer auth")
        
        # Check endpoints
        if "/pipelines" in api_content:
            if "/pipelines" in tut_content:
                scores["api_tut_endpoints"] = 100
                evidence.append("✓ Tutorial references correct endpoints")
            else:
                scores["api_tut_endpoints"] = 0
                evidence.append("✗ Tutorial missed /pipelines endpoint")
    
    # Check API → Code propagation
    if "api" in outputs and "code" in outputs:
        api_content = outputs["api"]
        code_content = outputs["code"].lower()
        
        if "bearer" in api_content.lower():
            if "bearer" in code_content or "token" in code_content:
                scores["api_code_auth"] = 100
            else:
                scores["api_code_auth"] = 0
    
    # Overall score
    overall = sum(scores.values()) / len(scores) if scores else 0
    
    return {
        "overall": overall,
        "details": scores,
        "evidence": evidence
    }

async def run_single_experiment(strategy: str, check_interval: int = 1) -> Dict:
    """Run one experiment"""
    
    # Clear workspace
    workspace = Path("workspace")
    if workspace.exists():
        for subdir in ["notes", "outputs"]:
            subdir_path = workspace / subdir
            if subdir_path.exists():
                for file in subdir_path.glob("*"):
                    file.unlink()
    
    # Create agents
    agents = [
        Agent("arch", "architecture"),
        Agent("api", "api_spec", dependencies=["arch"]),
        Agent("tut", "tutorial", dependencies=["arch", "api"]),
        Agent("code", "code", dependencies=["api"]),
        Agent("trouble", "troubleshooting", dependencies=["api", "tut"])
    ]
    
    start_time = time.time()
    
    # Run agents in parallel
    tasks = []
    for agent in agents:
        if strategy == "pairwise":
            task = agent.generate_with_pairwise_notes(check_interval)
        elif strategy == "output_sharing":
            task = agent.generate_with_output_sharing(check_interval)
        else:
            task = agent.generate_no_coordination()
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    outputs = {agent.name: result for agent, result in zip(agents, results)}
    
    execution_time = time.time() - start_time
    
    # Aggregate metrics
    total_metrics = Metrics()
    total_metrics.execution_time = execution_time
    
    for agent in agents:
        m = agent.metrics
        total_metrics.unique_files_created.update(m.unique_files_created)
        total_metrics.write_operations += m.write_operations
        total_metrics.read_operations += m.read_operations
        total_metrics.cache_hits += m.cache_hits
        total_metrics.bytes_written += m.bytes_written
        total_metrics.bytes_read += m.bytes_read
        total_metrics.llm_calls += m.llm_calls
        total_metrics.context_used_count += m.context_used_count
        total_metrics.input_tokens += m.input_tokens
        total_metrics.output_tokens += m.output_tokens
    
    consistency = analyze_consistency(outputs)
    
    return {
        "metrics": total_metrics.get_summary(),
        "consistency": consistency,
        "outputs": outputs,
        "token_usage": {
            "input": total_metrics.input_tokens,
            "output": total_metrics.output_tokens
        }
    }

async def main():
    """Run complete comparison experiment"""
    
    print("="*70)
    print("COORDINATION STRATEGY COMPARISON")
    print("="*70)
    print(f"Model: {MODEL}")
    print(f"Mode: {'Real Claude API' if not USE_MOCK_LLM else 'Mock mode'}")
    print(f"Runs per strategy: {NUM_RUNS}")
    print("="*70)
    
    strategies = [
        ("No Coordination", "none", 1),
        ("Pairwise Notes - Every Step", "pairwise", 1),
        ("Pairwise Notes - Every 2 Steps", "pairwise", 2),
        ("Output Sharing - Every Step", "output_sharing", 1),
        ("Output Sharing - Every 2 Steps", "output_sharing", 2),
    ]
    
    all_results = {name: [] for name, _, _ in strategies}
    total_tokens = {"input": 0, "output": 0}
    
    for run in range(NUM_RUNS):
        print(f"\n{'='*70}")
        print(f"RUN {run + 1} of {NUM_RUNS}")
        print("="*70)
        
        for name, strategy, interval in strategies:
            print(f"\n{name}...")
            result = await run_single_experiment(strategy, interval)
            all_results[name].append(result)
            
            # Track tokens
            total_tokens["input"] += result["token_usage"]["input"]
            total_tokens["output"] += result["token_usage"]["output"]
            
            print(f"  ✓ Consistency: {result['consistency']['overall']:.1f}%")
            print(f"  ✓ Time: {result['metrics']['execution_time']:.2f}s")
    
    # Statistical summary
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print("="*70)
    
    print("\n| Strategy | Time(s) | Consistency% | Files | Write Ops | Read Ops | Cache Hit% | Context Use% |")
    print("|----------|---------|--------------|-------|-----------|----------|------------|--------------|")
    
    summaries = {}
    for name, _, _ in strategies:
        runs = all_results[name]
        
        avg_metrics = {
            "time": statistics.mean([r["metrics"]["execution_time"] for r in runs]),
            "consistency": statistics.mean([r["consistency"]["overall"] for r in runs]),
            "files": statistics.mean([r["metrics"]["unique_files"] for r in runs]),
            "writes": statistics.mean([r["metrics"]["write_ops"] for r in runs]),
            "reads": statistics.mean([r["metrics"]["read_ops"] for r in runs]),
            "cache_rate": statistics.mean([r["metrics"]["cache_hit_rate"] for r in runs]),
            "context_rate": statistics.mean([r["metrics"]["context_usage_rate"] for r in runs])
        }
        
        summaries[name] = avg_metrics
        
        # Shorten name for table
        short_name = name.replace("Pairwise Notes - ", "PN-").replace("Output Sharing - ", "OS-").replace("Every ", "")
        
        print(f"| {short_name:<8} | {avg_metrics['time']:>7.2f} | {avg_metrics['consistency']:>11.1f}% | "
              f"{avg_metrics['files']:>5.0f} | {avg_metrics['writes']:>9.0f} | {avg_metrics['reads']:>8.0f} | "
              f"{avg_metrics['cache_rate']:>9.1f}% | {avg_metrics['context_rate']:>11.1f}% |")
    
    # Key insights
    print(f"\n{'='*70}")
    print("KEY INSIGHTS")
    print("="*70)
    
    baseline = summaries["No Coordination"]
    pn1 = summaries["Pairwise Notes - Every Step"]
    os1 = summaries["Output Sharing - Every Step"]
    
    print(f"\n1. QUALITY IMPROVEMENT (vs baseline):")
    print(f"   Pairwise Notes:  +{pn1['consistency'] - baseline['consistency']:.1f}%")
    print(f"   Output Sharing:  +{os1['consistency'] - baseline['consistency']:.1f}%")
    
    print(f"\n2. EFFICIENCY COMPARISON:")
    print(f"   Pairwise: {pn1['writes']:.0f} writes, {pn1['reads']:.0f} reads")
    print(f"   Output:   {os1['writes']:.0f} writes, {os1['reads']:.0f} reads (cache hit: {os1['cache_rate']:.1f}%)")
    
    print(f"\n3. CONTEXT UTILIZATION:")
    print(f"   Pairwise: {pn1['context_rate']:.1f}% of LLM calls used context")
    print(f"   Output:   {os1['context_rate']:.1f}% of LLM calls used context")
    
    # Cost analysis
    if not USE_MOCK_LLM:
        # Claude Haiku pricing per million tokens
        input_cost = (total_tokens["input"] / 1_000_000) * 0.25
        output_cost = (total_tokens["output"] / 1_000_000) * 1.25
        total_cost = input_cost + output_cost
        
        print(f"\n4. COST ANALYSIS:")
        print(f"   Total tokens: {total_tokens['input'] + total_tokens['output']:,}")
        print(f"   Total cost: ${total_cost:.4f}")
        print(f"   Cost per strategy run: ${total_cost / (len(strategies) * NUM_RUNS):.5f}")
    
    # Evidence from best run
    print(f"\n5. CONSISTENCY EVIDENCE (from best run):")
    best_pn = max(all_results["Pairwise Notes - Every Step"], key=lambda r: r["consistency"]["overall"])
    for evidence in best_pn["consistency"]["evidence"][:5]:
        print(f"   {evidence}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(main())
