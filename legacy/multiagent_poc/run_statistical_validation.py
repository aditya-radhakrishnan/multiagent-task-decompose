#!/usr/bin/env python3
"""
Run complete statistical validation study
"""

import subprocess
import sys

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         STATISTICAL VALIDATION STUDY                     ║
╚══════════════════════════════════════════════════════════╝

This will run a batch of experiments to validate auto-decomposition
with statistical rigor.

Default: n=5 per complexity tier (15 total experiments)
- Simple tasks: 5 experiments
- Medium tasks: 5 experiments  
- Complex tasks: 5 experiments

Each experiment runs BOTH approaches (30 agent calls total)

Estimated time: 30-60 minutes
Estimated cost: $5-8

You can change n with: python run_statistical_validation.py <n>
""")
    
    n = 5  # Default
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
        except ValueError:
            print(f"Invalid n: {sys.argv[1]}")
            sys.exit(1)
    
    print(f"\nRunning with n={n} per complexity tier ({n*3} total experiments)")
    input("Press Enter to continue or Ctrl+C to cancel...")
    
    # Step 1: Run batch experiments
    print("\n" + "="*60)
    print("STEP 1: Running batch experiments")
    print("="*60)
    
    result = subprocess.run(f"python batch_runner.py {n}", shell=True)
    if result.returncode != 0:
        print("Error running batch experiments")
        sys.exit(1)
    
    # Step 2: Analyze results
    print("\n" + "="*60)
    print("STEP 2: Analyzing results")
    print("="*60)
    
    result = subprocess.run("python analyze_results.py", shell=True)
    if result.returncode != 0:
        print("Error analyzing results")
        sys.exit(1)
    
    print("""
✓ Statistical validation complete!

📊 Results:
  - ./batch_results/batch_results.json - Raw data
  - ./batch_results/statistical_report.md - Statistical analysis

Key findings:
  - Summary statistics (mean, std dev) by complexity
  - Win rates for each approach
  - Effect sizes (Cohen's d)
  - Recommendations based on data

Next: Review the statistical report to understand when auto-decomposition
provides significant benefits.
""")


if __name__ == "__main__":
    main()
