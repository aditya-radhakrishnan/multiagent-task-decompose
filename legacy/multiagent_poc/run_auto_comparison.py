#!/usr/bin/env python3
"""
Complete comparison: Auto-decomposition vs Single Agent
"""

import subprocess
import sys
import py_compile
import os

def check_syntax(filename):
    """Check if a Python file has valid syntax"""
    try:
        py_compile.compile(filename, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)

def validate_scripts():
    """Validate syntax of all required scripts"""
    scripts = ['auto_orchestrator.py', 'auto_comparison.py']
    
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

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║   AUTO-DECOMPOSITION VS SINGLE AGENT COMPARISON          ║
╚══════════════════════════════════════════════════════════╝

This will:
1. Run auto-decomposition approach (spawns multiple agents)
2. Run single agent approach (one agent does everything)
3. Compare quality, cost, and efficiency

Available task types:
  simple    - API endpoint (~500 LOC)
  complex   - Auth system (~1000 LOC)
  ecommerce - Product catalog system (~2000 LOC)
  payment   - Payment integration system (~1500 LOC)
  analytics - Analytics dashboard system (~2000 LOC)

Estimated time: 2-5 minutes depending on task
Estimated cost: $0.30-$1.00 depending on task
""")
    
    # Validate syntax
    validate_scripts()
    
    # Check for task argument
    task_type = "simple"
    if len(sys.argv) > 1:
        task_type = sys.argv[1]
        if task_type not in ['simple', 'complex', 'ecommerce', 'payment', 'analytics']:
            print(f"Unknown task type: {task_type}")
            print("Use: simple, complex, ecommerce, payment, or analytics")
            sys.exit(1)
    
    print(f"Task type: {task_type}\n")
    input("Press Enter to continue...")
    
    # Step 1: Run auto-decomposition
    print(f"\n{'='*60}")
    print("STEP 1/2: Running auto-decomposition approach")
    print(f"{'='*60}")
    
    result = subprocess.run(f"python run_auto.py {task_type}", shell=True)
    if result.returncode != 0:
        print("Error running auto-decomposition")
        sys.exit(1)
    
    # Step 2: Run comparison
    print(f"\n{'='*60}")
    print("STEP 2/2: Running single agent and comparing")
    print(f"{'='*60}")
    
    cmd = "python auto_comparison.py"
    if task_type == "complex":
        cmd += " complex"
    elif task_type == "ecommerce":
        cmd += " ecommerce"
    elif task_type == "payment":
        cmd += " payment"
    elif task_type == "analytics":
        cmd += " analytics"
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("Error running comparison")
        sys.exit(1)
    
    print("""
✓ Comparison complete!

📊 Results:
  - ./auto_comparison_output/approach_comparison.md - Detailed analysis
  - ./auto_comparison_output/summary.md - Quick overview

📁 Raw outputs:
  - ./auto_comparison_output/single_agent_output.md
  - ./auto_poc_output/state/ - Auto-decomposition results
  - ./auto_poc_output/debug/task_decomposition.json - How task was decomposed

Next: Review the comparison to see which approach worked better!
""")

if __name__ == "__main__":
    main()
