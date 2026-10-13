"""
Quick fix to add estimated_output_tokens to meta_prompt_tester.py results
Run this after meta_prompt_tester.py to patch the results
"""

import json
from pathlib import Path

# Load existing results
results_file = Path("meta_prompt_test/meta_prompt_results.json")
if not results_file.exists():
    print("No results file found")
    exit(1)

with open(results_file) as f:
    data = json.load(f)

# Map from decision_analysis.md - these are the estimates from the meta-prompt
estimates = {
    "simple_1": "3-5k",
    "simple_2": "4-6k", 
    "medium_1": "6-8k",
    "medium_2": "12-15k",
    "complex_1": "15-20k",
    "complex_3": "15-20k"
}

# Add estimated_output_tokens to each decision
for decision in data['decisions']:
    task_id = decision['task_id']
    decision['estimated_output_tokens'] = estimates.get(task_id, "unknown")

# Save patched results
with open(results_file, 'w') as f:
    json.dump(data, f, indent=2)

print("✓ Patched meta_prompt_results.json with token estimates")
print("Run: python calibration_analyzer.py")
