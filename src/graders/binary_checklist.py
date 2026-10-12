"""
Universal Binary Checklist Grader
Task-agnostic evaluation with 12 binary requirements
"""

import anthropic
import os
import json

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Max characters of output shown to the grader. The original 10,000-char cut-off
# would hide most of a multi-agent output and bias scores, so it is much higher here.
MAX_OUTPUT_CHARS = 120000
GRADER_VERSION = "binary_checklist_v1"

# Universal requirements that work for any software task
REQUIREMENTS = {
    "all_components_present": {
        "question": "Are all components mentioned in the task requirements implemented (not stubbed or missing)?",
        "criteria": "Check if every feature/component from requirements exists in the code"
    },
    "no_placeholders": {
        "question": "Are there NO TODO comments, '...' ellipses, or 'implement this later' placeholders?",
        "criteria": "Code should be complete, not have unfinished sections"
    },
    "setup_instructions": {
        "question": "Are installation/setup instructions or dependency files included?",
        "criteria": "Should have requirements.txt, package.json, or setup instructions"
    },
    "syntactically_valid": {
        "question": "Does the code have no syntax errors and are all imports valid?",
        "criteria": "Code should be parseable and imports should exist"
    },
    "logically_sound": {
        "question": "Does the core logic appear correct (algorithms, API calls, data flow)?",
        "criteria": "Implementation should make logical sense for the task"
    },
    "error_handling": {
        "question": "Is error handling included for expected failure cases?",
        "criteria": "Should handle common errors like network failures, invalid input, etc."
    },
    "structured_well": {
        "question": "Is code organized into logical modules/functions/classes?",
        "criteria": "Should have reasonable structure, not all in one function"
    },
    "production_config": {
        "question": "Are necessary configs included (env vars, constants, not hardcoded secrets)?",
        "criteria": "Should use config files or env vars for sensitive/changeable values"
    },
    "security_considered": {
        "question": "Are basic security practices followed (input validation, auth checks where needed)?",
        "criteria": "Should validate inputs and check auth where applicable"
    },
    "components_aligned": {
        "question": "If multiple components (backend/frontend), do they use compatible interfaces?",
        "criteria": "API contracts should match, types should align"
    },
    "dependencies_documented": {
        "question": "Are external dependencies documented or managed?",
        "criteria": "Should list what packages/services are needed"
    },
    "executable": {
        "question": "Could the code reasonably be run by following provided instructions?",
        "criteria": "Should be runnable without major missing pieces"
    }
}


def evaluate_output(task_description: str, output: str, approach_name: str) -> dict:
    """
    Evaluate a single output using binary checklist
    
    Returns:
        {
            "requirements": {req_id: bool, ...},
            "score": int,  # number of requirements met
            "total": 12,
            "percentage": float
        }
    """
    
    # Build evaluation prompt
    requirements_text = ""
    for req_id, req_info in REQUIREMENTS.items():
        requirements_text += f"\n{req_id}: {req_info['question']}\n"
        requirements_text += f"   Criteria: {req_info['criteria']}\n"
    
    prompt = f"""You are evaluating code implementation against a binary checklist.

TASK REQUIREMENTS:
{task_description}

CODE TO EVALUATE (from {approach_name}):
{output[:MAX_OUTPUT_CHARS]}

EVALUATION CHECKLIST:

For each requirement below, answer ONLY "true" or "false" based on whether the code meets the criteria.

{requirements_text}

Respond with ONLY a JSON object in this exact format:
{{
  "all_components_present": true/false,
  "no_placeholders": true/false,
  "setup_instructions": true/false,
  "syntactically_valid": true/false,
  "logically_sound": true/false,
  "error_handling": true/false,
  "structured_well": true/false,
  "production_config": true/false,
  "security_considered": true/false,
  "components_aligned": true/false,
  "dependencies_documented": true/false,
  "executable": true/false
}}

Provide ONLY the JSON, no other text.
"""
    
    # Call evaluator
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response = message.content[0].text
    
    # Parse JSON response
    import re
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    results = None
    if json_match:
        try:
            results = json.loads(json_match.group())
        except json.JSONDecodeError:
            results = None
    if results is None:
        # Fallback: all false if can't parse
        results = {req_id: False for req_id in REQUIREMENTS.keys()}
    
    # Calculate score
    results = {k: bool(results.get(k, False)) for k in REQUIREMENTS}
    score = sum(results.values())
    percentage = (score / len(REQUIREMENTS)) * 100
    
    return {
        "requirements": results,
        "score": score,
        "total": len(REQUIREMENTS),
        "percentage": round(percentage, 1),
        "output_chars": len(output),
        "truncated_for_grader": len(output) > MAX_OUTPUT_CHARS,
    }


def evaluate_comparison(task_description: str, single_output: str, parallel_output: str, 
                       best_of_n_output: str = None) -> dict:
    """
    Evaluate all approaches for a task
    
    Returns:
        {
            "task_id": str,
            "grader": "binary_checklist_v1",
            "single_agent": {...},
            "parallel_multi": {...},
            "best_of_n": {...} or None
        }
    """
    
    print("Evaluating with Binary Checklist...")
    
    results = {
        "grader": "binary_checklist_v1",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }
    
    # Evaluate single agent
    print("  - Evaluating Single Agent...")
    results["single_agent"] = evaluate_output(task_description, single_output, "Single Agent")
    
    # Evaluate parallel multi-agent
    print("  - Evaluating Parallel Multi-Agent...")
    results["parallel_multi"] = evaluate_output(task_description, parallel_output, "Parallel Multi-Agent")
    
    # Evaluate best-of-N if provided
    if best_of_n_output:
        print("  - Evaluating Best-of-N...")
        results["best_of_n"] = evaluate_output(task_description, best_of_n_output, "Best-of-N")
    
    return results
