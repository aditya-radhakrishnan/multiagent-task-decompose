"""
Experiment comparing two coordination strategies:
1. Pairwise Notes: Agents write specific notes for other agents
2. Output Sharing: Agents write their outputs to files that others can read
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from anthropic import Anthropic
import statistics

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
USE_MOCK_LLM = not bool(ANTHROPIC_API_KEY)
MODEL = "claude-3-haiku-20240307"
NUM_RUNS = 3

if not USE_MOCK_LLM:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    print("Using Claude for generation")
else:
    print("Using mock responses (no API key found)")

class Agent:
    """Agent that can use different coordination strategies"""
    
    def __init__(self, name: str, role: str, dependencies: List[str] = None):
        self.name = name
        self.role = role
        self.dependencies = dependencies or []
        self.workspace = Path("workspace")
        self.workspace.mkdir(exist_ok=True)
        
        # Metrics
        self.files_read = 0
        self.files_written = 0
        self.relevant_content_found = 0
        self.llm_calls = 0
        self.bytes_read = 0
        self.bytes_written = 0
    
    def get_steps(self) -> List[Tuple[str, str]]:
        """Define work steps for each role"""
        steps = {
            "architecture": [
                ("Define Components", "List the main system components and their purposes"),
                ("Design Data Layer", "Describe databases, caching, and data flow"),
                ("Plan Scaling", "Explain how the system scales")
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
    
    def call_llm(self, prompt: str, with_context: bool = False) -> str:
        """Call LLM or return mock response"""
        self.llm_calls += 1
        
        if USE_MOCK_LLM:
            # Mock responses that vary by step
            mock_responses = {
                "architecture": [
                    "System uses microservices architecture with API Gateway routing requests. PostgreSQL for data persistence.",
                    "Data layer includes PostgreSQL for transactional data, Redis for caching, and S3 for blob storage.",
                    "Horizontal scaling via Kubernetes, auto-scaling based on CPU and memory metrics."
                ],
                "api_spec": [
                    "Authentication via Bearer tokens in Authorization header. Tokens expire after 24 hours.",
                    "Main endpoints: POST /pipelines, GET /pipelines/{id}, PUT /pipelines/{id}, DELETE /pipelines/{id}",
                    "Success returns 200/201, auth errors return 401, rate limit returns 429, server errors return 500"
                ],
                "tutorial": [
                    "Get your API key from dashboard.example.com. Set environment variable API_KEY.",
                    "First call: curl -H 'Authorization: Bearer YOUR_KEY' https://api.example.com/pipelines",
                    "Complete example: Create pipeline, add transformations, execute, and poll for results."
                ],
                "code": [
                    "DataFlowClient class initialized with API key, base URL, and optional timeout settings.",
                    "Methods: create_pipeline(name, config), get_pipeline(id), update_pipeline(id, config), delete_pipeline(id)",
                    "Implements exponential backoff for retries, catches network errors and API errors separately."
                ],
                "troubleshooting": [
                    "Common errors: 401 (invalid/expired token), 429 (rate limited), 500 (server error), timeout",
                    "For 401: Check token expiry. For 429: Implement backoff. For 500: Check status page.",
                    "Enable debug logging with DEBUG=true. Use request IDs for support. Check network connectivity."
                ]
            }
            
            responses = mock_responses.get(self.role, ["Generic content"])
            step_index = min(self.current_step if hasattr(self, 'current_step') else 0, len(responses) - 1)
            response = responses[step_index]
            
            if with_context:
                response += " [Context integrated]"
            
            return response
        
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=200,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"[LLM Error] Fallback response for {self.role}"
    
    # ========== STRATEGY 1: Pairwise Notes ==========
    
    def write_pairwise_note(self, recipient: str, content: str, topic: str = "general"):
        """Write a note specifically for another agent"""
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
            self.bytes_written += len(data.encode())
        
        self.files_written += 1
    
    def read_pairwise_notes(self) -> Dict[str, List[str]]:
        """Read notes addressed to this agent"""
        notes_dir = self.workspace / "notes"
        if not notes_dir.exists():
            return {}
        
        all_notes = {}
        for dep in self.dependencies:
            note_file = notes_dir / f"{dep}_to_{self.name}.jsonl"
            if note_file.exists():
                self.files_read += 1
                notes = []
                with open(note_file, 'r') as f:
                    content = f.read()
                    self.bytes_read += len(content.encode())
                    
                    for line in content.strip().split('\n'):
                        if line:
                            try:
                                note = json.loads(line)
                                notes.append(note['content'])
                            except:
                                pass
                
                if notes:
                    all_notes[dep] = notes
                    self.relevant_content_found += len(notes)
        
        return all_notes
    
    async def generate_with_pairwise_notes(self, check_interval: int = 1) -> str:
        """Generate using pairwise note coordination"""
        steps = self.get_steps()
        results = []
        
        print(f"  {self.name}: Starting with PAIRWISE notes (check every {check_interval} steps)")
        
        for i, (step_name, step_desc) in enumerate(steps):
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
            prompt = f"""Role: {self.role}
Step: {step_name} - {step_desc}
Context from other agents: {context if context else 'No notes available'}

Generate 2-3 sentences for this step."""
            
            content = self.call_llm(prompt, bool(context))
            results.append(f"### {step_name}\n{content}")
            
            # Write notes for others based on what we generated
            if self.role == "architecture" and i == 0:
                self.write_pairwise_note("api_spec", "Using PostgreSQL and Redis", "infrastructure")
                self.write_pairwise_note("code", "Microservices architecture", "architecture")
            elif self.role == "api_spec" and i == 1:
                self.write_pairwise_note("tutorial", "Endpoints: POST /pipelines, GET /pipelines/{id}", "endpoints")
                self.write_pairwise_note("code", "Bearer token authentication required", "auth")
                self.write_pairwise_note("troubleshooting", "Error codes: 401, 429, 500", "errors")
            elif self.role == "tutorial" and i == 0:
                self.write_pairwise_note("troubleshooting", "Users struggle with auth setup", "pain_point")
            
            await asyncio.sleep(0.05)
        
        return "\n\n".join(results)
    
    # ========== STRATEGY 2: Output File Sharing ==========
    
    def write_output_file(self, content: str, step_name: str):
        """Write current output to agent's output file"""
        output_file = self.workspace / "outputs" / f"{self.name}_output.md"
        output_file.parent.mkdir(exist_ok=True)
        
        # Append new content with timestamp
        with open(output_file, 'a') as f:
            section = f"\n## [{datetime.now().strftime('%H:%M:%S')}] {step_name}\n{content}\n"
            f.write(section)
            self.bytes_written += len(section.encode())
        
        self.files_written += 1
    
    def read_dependency_outputs(self) -> Dict[str, str]:
        """Read the output files of dependencies"""
        outputs_dir = self.workspace / "outputs"
        if not outputs_dir.exists():
            return {}
        
        dependency_outputs = {}
        for dep in self.dependencies:
            output_file = outputs_dir / f"{dep}_output.md"
            if output_file.exists():
                self.files_read += 1
                with open(output_file, 'r') as f:
                    content = f.read()
                    self.bytes_read += len(content.encode())
                    
                    # Only take last 500 chars to avoid overwhelming context
                    if content:
                        dependency_outputs[dep] = content[-500:]
                        self.relevant_content_found += 1
        
        return dependency_outputs
    
    async def generate_with_output_sharing(self, check_interval: int = 1) -> str:
        """Generate using output file sharing coordination"""
        steps = self.get_steps()
        results = []
        
        print(f"  {self.name}: Starting with OUTPUT SHARING (check every {check_interval} steps)")
        
        for i, (step_name, step_desc) in enumerate(steps):
            self.current_step = i
            
            # Check dependency outputs based on interval
            context = ""
            if i % check_interval == 0 and self.dependencies:
                outputs = self.read_dependency_outputs()
                if outputs:
                    context_parts = []
                    for dep, output in outputs.items():
                        # Extract key information from output
                        context_parts.append(f"From {dep}'s output:\n{output[:200]}...")
                    context = "\n---\n".join(context_parts)
            
            # Generate content
            prompt = f"""Role: {self.role}
Step: {step_name} - {step_desc}
Available outputs from dependencies: {context if context else 'No outputs available yet'}

Generate 2-3 sentences for this step. Build on the available information."""
            
            content = self.call_llm(prompt, bool(context))
            results.append(f"### {step_name}\n{content}")
            
            # Write output to file (available for all other agents)
            self.write_output_file(content, step_name)
            
            await asyncio.sleep(0.05)
        
        return "\n\n".join(results)
    
    # ========== STRATEGY 3: No Coordination (Baseline) ==========
    
    async def generate_no_coordination(self) -> str:
        """Generate without any coordination"""
        steps = self.get_steps()
        results = []
        
        print(f"  {self.name}: Starting with NO coordination")
        
        for i, (step_name, step_desc) in enumerate(steps):
            self.current_step = i
            
            prompt = f"""Role: {self.role}
Step: {step_name} - {step_desc}

Generate 2-3 sentences for this step."""
            
            content = self.call_llm(prompt, False)
            results.append(f"### {step_name}\n{content}")
            
            await asyncio.sleep(0.05)
        
        return "\n\n".join(results)

def analyze_consistency(outputs: Dict[str, str]) -> Dict[str, float]:
    """Analyze consistency between agent outputs"""
    
    scores = {}
    
    # Check if API spec mentions architecture terms
    if "arch" in outputs and "api" in outputs:
        arch_terms = ["PostgreSQL", "Redis", "microservice", "Kubernetes", "Gateway"]
        matches = sum(1 for term in arch_terms if term.lower() in outputs["api"].lower())
        scores["api_uses_arch"] = (matches / len(arch_terms)) * 100
    
    # Check if tutorial references API endpoints
    if "api" in outputs and "tut" in outputs:
        api_terms = ["/pipelines", "Bearer", "POST", "GET", "authorization"]
        matches = sum(1 for term in api_terms if term.lower() in outputs["tut"].lower())
        scores["tutorial_uses_api"] = (matches / len(api_terms)) * 100
    
    # Check if code implements API patterns
    if "api" in outputs and "code" in outputs:
        code_terms = ["pipeline", "Bearer", "client", "401", "429"]
        matches = sum(1 for term in code_terms if term.lower() in outputs["code"].lower())
        scores["code_follows_api"] = (matches / len(code_terms)) * 100
    
    # Check if troubleshooting addresses real issues
    if "trouble" in outputs:
        trouble_terms = ["401", "429", "token", "rate", "debug"]
        matches = sum(1 for term in trouble_terms if term.lower() in outputs["trouble"].lower())
        scores["troubleshooting_complete"] = (matches / len(trouble_terms)) * 100
    
    # Overall consistency
    scores["overall"] = sum(scores.values()) / len(scores) if scores else 0
    
    return scores

async def run_single_experiment(strategy: str, check_interval: int = 1) -> Dict:
    """Run a single experiment with the specified strategy"""
    
    # Clear workspace
    workspace = Path("workspace")
    if workspace.exists():
        for subdir in ["notes", "outputs"]:
            subdir_path = workspace / subdir
            if subdir_path.exists():
                for file in subdir_path.glob("*"):
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
    
    # Run agents in parallel with specified strategy
    tasks = []
    for agent in agents:
        if strategy == "pairwise":
            task = agent.generate_with_pairwise_notes(check_interval)
        elif strategy == "output_sharing":
            task = agent.generate_with_output_sharing(check_interval)
        else:  # no_coordination
            task = agent.generate_no_coordination()
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    outputs = {agent.name: result for agent, result in zip(agents, results)}
    
    execution_time = time.time() - start_time
    
    # Collect metrics
    total_files_read = sum(a.files_read for a in agents)
    total_files_written = sum(a.files_written for a in agents)
    total_bytes_read = sum(a.bytes_read for a in agents)
    total_bytes_written = sum(a.bytes_written for a in agents)
    total_relevant_content = sum(a.relevant_content_found for a in agents)
    total_llm_calls = sum(a.llm_calls for a in agents)
    
    consistency = analyze_consistency(outputs)
    
    return {
        "execution_time": execution_time,
        "files_read": total_files_read,
        "files_written": total_files_written,
        "bytes_read": total_bytes_read,
        "bytes_written": total_bytes_written,
        "relevant_content_found": total_relevant_content,
        "llm_calls": total_llm_calls,
        "consistency": consistency,
        "outputs": outputs
    }

async def main():
    """Compare pairwise notes vs output sharing vs no coordination"""
    
    print("="*70)
    print("COORDINATION STRATEGY COMPARISON")
    print("Pairwise Notes vs Output File Sharing vs No Coordination")
    print("="*70)
    
    strategies = [
        ("No Coordination", "none", 1),
        ("Pairwise Notes - Check Every Step", "pairwise", 1),
        ("Pairwise Notes - Check Every 2 Steps", "pairwise", 2),
        ("Output Sharing - Check Every Step", "output_sharing", 1),
        ("Output Sharing - Check Every 2 Steps", "output_sharing", 2),
    ]
    
    all_results = {name: [] for name, _, _ in strategies}
    
    # Run multiple times for statistical validity
    for run in range(NUM_RUNS):
        print(f"\n{'='*70}")
        print(f"RUN {run + 1} of {NUM_RUNS}")
        print("="*70)
        
        for name, strategy, interval in strategies:
            print(f"\nTesting: {name}")
            result = await run_single_experiment(strategy, interval)
            all_results[name].append(result)
            print(f"  Consistency: {result['consistency']['overall']:.1f}%")
            print(f"  Time: {result['execution_time']:.2f}s")
            print(f"  Files R/W: {result['files_read']}/{result['files_written']}")
    
    # Statistical summary
    print(f"\n{'='*70}")
    print("STATISTICAL SUMMARY (averaged over " + str(NUM_RUNS) + " runs)")
    print("="*70)
    
    print("\n| Strategy                          | Time(s) | Consistency | Files R | Files W | Bytes R | Bytes W |")
    print("|-----------------------------------|---------|-------------|---------|---------|---------|---------|")
    
    summary = {}
    for name, _, _ in strategies:
        runs = all_results[name]
        
        avg_time = statistics.mean([r['execution_time'] for r in runs])
        avg_consistency = statistics.mean([r['consistency']['overall'] for r in runs])
        avg_files_read = statistics.mean([r['files_read'] for r in runs])
        avg_files_written = statistics.mean([r['files_written'] for r in runs])
        avg_bytes_read = statistics.mean([r['bytes_read'] for r in runs])
        avg_bytes_written = statistics.mean([r['bytes_written'] for r in runs])
        
        summary[name] = {
            'time': avg_time,
            'consistency': avg_consistency,
            'files_read': avg_files_read,
            'files_written': avg_files_written,
            'bytes_read': avg_bytes_read,
            'bytes_written': avg_bytes_written
        }
        
        print(f"| {name:<33} | {avg_time:>7.2f} | {avg_consistency:>10.1f}% | {avg_files_read:>7.0f} | "
              f"{avg_files_written:>7.0f} | {avg_bytes_read:>7.0f} | {avg_bytes_written:>7.0f} |")
    
    # Key comparisons
    print(f"\n{'='*70}")
    print("KEY INSIGHTS")
    print("="*70)
    
    baseline = summary["No Coordination"]
    pairwise_1 = summary["Pairwise Notes - Check Every Step"]
    output_1 = summary["Output Sharing - Check Every Step"]
    
    print("\n1. QUALITY COMPARISON (vs No Coordination):")
    print(f"   Pairwise Notes:  +{pairwise_1['consistency'] - baseline['consistency']:.1f}% consistency")
    print(f"   Output Sharing:  +{output_1['consistency'] - baseline['consistency']:.1f}% consistency")
    
    print("\n2. EFFICIENCY COMPARISON:")
    print(f"   Pairwise Notes:  {pairwise_1['files_written']:.0f} files written, {pairwise_1['bytes_written']:.0f} bytes")
    print(f"   Output Sharing:  {output_1['files_written']:.0f} files written, {output_1['bytes_written']:.0f} bytes")
    
    print("\n3. SCALABILITY:")
    print(f"   Pairwise: O(N²) potential connections (N×N matrix)")
    print(f"   Output:   O(N) files (one per agent)")
    
    print("\n4. COMPLEXITY:")
    print(f"   Pairwise: Requires deciding what to write to whom")
    print(f"   Output:   Simply write everything, readers filter")
    
    # Determine winner
    if output_1['consistency'] > pairwise_1['consistency'] - 5:  # Within 5% or better
        if output_1['files_written'] < pairwise_1['files_written']:
            print("\n✅ RECOMMENDATION: Output Sharing")
            print("   - Similar or better quality")
            print("   - Simpler implementation")
            print("   - Better scalability")
    else:
        print("\n✅ RECOMMENDATION: Pairwise Notes")
        print("   - Significantly better quality")
        print("   - Worth the extra complexity")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(main())
