#!/usr/bin/env python3
"""
Complete comparison of coordination approaches.
Runs all experiments and generates comparative analysis.
"""

import sys
import subprocess
import py_compile
import os

def check_syntax(filename):
    """Check if a Python file has valid syntax"""
    try:
        py_compile.compile(filename, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)

def validate_all_scripts():
    """Validate syntax of all required scripts before running"""
    scripts = ['orchestrator.py', 'ai_evaluator.py', 'comparison.py']
    
    print("Validating script syntax...")
    all_valid = True
    
    for script in scripts:
        if not os.path.exists(script):
            print(f"  ✗ {script} - NOT FOUND")
            all_valid = False
            continue
            
        valid, error = check_syntax(script)
        if valid:
            print(f"  ✓ {script}")
        else:
            print(f"  ✗ {script} - SYNTAX ERROR")
            print(f"    {error}")
            all_valid = False
    
    if not all_valid:
        print("\n❌ Syntax errors detected. Fix them before running.")
        sys.exit(1)
    
    print("✓ All scripts validated\n")

def run_command(cmd, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error running: {cmd}")
        sys.exit(1)

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║     MULTI-AGENT COORDINATION COMPARISON EXPERIMENT       ║
╚══════════════════════════════════════════════════════════╝

This will run three approaches to the same task:
1. Multi-agent with state file coordination
2. Single agent doing everything
3. Independent agents (no coordination)

Then compare quality, cost, and efficiency.

Estimated time: 2-3 minutes
Estimated cost: $0.30-0.50
""")
    
    # Validate syntax first
    validate_all_scripts()
    
    input("Press Enter to continue...")
    
    # Step 1: Run coordinated multi-agent approach
    run_command(
        "python orchestrator.py",
        "STEP 1/3: Running coordinated multi-agent approach"
    )
    
    # Step 2: Run comparison of all approaches
    run_command(
        "python comparison.py",
        "STEP 2/3: Running alternative approaches"
    )
    
    # Step 3: Evaluate
    print(f"\n{'='*60}")
    print("STEP 3/3: Generating final comparison report")
    print(f"{'='*60}\n")
    
    print("""
✓ Comparison complete!

📊 Results:
  - ./comparison_output/comparison_summary.md
  - ./comparison_output/quality_comparison.md

📁 Raw outputs:
  - ./comparison_output/single_agent_output.md
  - ./comparison_output/independent_agents_output.md
  - ./poc_output/state/ (coordinated agents)

Next: Review the comparison reports to see which approach worked best!
""")

if __name__ == "__main__":
    main()
