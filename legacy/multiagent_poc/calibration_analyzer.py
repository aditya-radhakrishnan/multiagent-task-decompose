"""
Calibration Analyzer - Extracts patterns from real execution data
Provides recommendations for improving meta-prompt accuracy
"""

import json
from pathlib import Path
from collections import defaultdict


def load_calibration_results():
    """Load calibration results from file"""
    results_file = Path("calibration_output/results.json")
    if not results_file.exists():
        print("❌ No calibration results found. Run calibration_runner.py first.")
        return []
    
    with open(results_file) as f:
        return json.load(f)


def load_meta_prompt_predictions():
    """Load meta-prompt predictions from meta_prompt_test"""
    predictions_file = Path("meta_prompt_test/meta_prompt_results.json")
    if not predictions_file.exists():
        print("⚠️  No meta-prompt predictions found. Run meta_prompt_tester.py first.")
        return {}
    
    with open(predictions_file) as f:
        data = json.load(f)
        predictions = {}
        for decision in data.get('decisions', []):
            predictions[decision['task_id']] = {
                'predicted': decision['actual'],
                'reasoning': decision.get('reasoning', ''),
                'estimated_tokens': decision.get('estimated_output_tokens', 'unknown')
            }
        return predictions


def analyze_ground_truth_accuracy(results):
    """Check if ground truth labels are accurate based on actual runs"""
    
    analysis = {
        'confirmed': [],
        'questionable': [],
        'failed': []
    }
    
    for r in results:
        if not r.get('success'):
            continue
        
        validation = r.get('ground_truth_validation', '')
        
        if 'CONFIRMED' in validation:
            analysis['confirmed'].append(r)
        elif 'QUESTIONABLE' in validation:
            analysis['questionable'].append(r)
        elif 'FAILED' in validation:
            analysis['failed'].append(r)
    
    return analysis


def analyze_token_estimation_accuracy(results, predictions):
    """Compare predicted token counts vs actual"""
    
    comparison = []
    
    for r in results:
        if not r.get('success'):
            continue
        
        task_id = r['task_id']
        actual_tokens = r['actual_output_tokens']
        
        pred = predictions.get(task_id, {})
        estimated = pred.get('estimated_tokens', 'unknown')
        
        # Parse estimated range
        if estimated != 'unknown':
            estimated_str = estimated.replace('k', '000').replace('+', '')
            
            if '-' in estimated_str:
                low, high = estimated_str.split('-')
                est_low, est_high = int(low), int(high)
                est_mid = (est_low + est_high) // 2
            else:
                try:
                    est_mid = int(estimated_str)
                    est_low = est_high = est_mid
                except:
                    est_mid = est_low = est_high = 0
            
            error = actual_tokens - est_mid
            error_pct = (error / est_mid * 100) if est_mid > 0 else 0
            
            within_range = est_low <= actual_tokens <= est_high
        else:
            error = 0
            error_pct = 0
            within_range = None
            est_low = est_high = est_mid = 0
        
        comparison.append({
            'task': r['task_name'],
            'task_id': task_id,
            'ground_truth': r['ground_truth'],
            'estimated': estimated,
            'est_range': (est_low, est_high),
            'actual': actual_tokens,
            'error': error,
            'error_pct': error_pct,
            'within_range': within_range,
            'truncated': r['truncated']
        })
    
    return comparison


def generate_meta_prompt_recommendations(results, predictions, token_analysis):
    """Generate specific recommendations for improving meta-prompt"""
    
    recommendations = []
    
    # Check ground truth accuracy
    gt_analysis = analyze_ground_truth_accuracy(results)
    
    if gt_analysis['failed']:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Ground Truth Errors',
            'issue': f"{len(gt_analysis['failed'])} tasks marked SINGLE_AGENT but truncated",
            'tasks': [r['task_name'] for r in gt_analysis['failed']],
            'action': 'Update ground truth to DECOMPOSE for these tasks',
            'impact': 'Meta-prompt cannot learn correct patterns with wrong labels'
        })
    
    if gt_analysis['questionable']:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Questionable Ground Truth',
            'issue': f"{len(gt_analysis['questionable'])} tasks marked DECOMPOSE but single agent completed",
            'tasks': [r['task_name'] for r in gt_analysis['questionable']],
            'action': 'Review these tasks - may not need decomposition',
            'impact': 'Meta-prompt may be over-predicting DECOMPOSE'
        })
    
    # Token estimation errors
    large_errors = [t for t in token_analysis if abs(t['error_pct']) > 50]
    if large_errors:
        overestimated = [t for t in large_errors if t['error'] < 0]
        underestimated = [t for t in large_errors if t['error'] > 0]
        
        if overestimated:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Token Overestimation',
                'issue': f"{len(overestimated)} tasks overestimated by >50%",
                'tasks': [t['task'] for t in overestimated],
                'action': 'Add calibration examples showing actual token counts',
                'impact': 'False positives for DECOMPOSE (recommending it when not needed)'
            })
        
        if underestimated:
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Token Underestimation',
                'issue': f"{len(underestimated)} tasks underestimated by >50%",
                'tasks': [t['task'] for t in underestimated],
                'action': 'Add examples of larger implementations',
                'impact': 'False negatives for DECOMPOSE (missing when needed)'
            })
    
    # Check for systematic patterns
    single_agent_tasks = [r for r in results if r.get('success') and r['ground_truth'] == 'SINGLE_AGENT']
    if single_agent_tasks:
        max_tokens = max(t['actual_output_tokens'] for t in single_agent_tasks)
        avg_tokens = sum(t['actual_output_tokens'] for t in single_agent_tasks) / len(single_agent_tasks)
        
        recommendations.append({
            'priority': 'INFO',
            'category': 'Single Agent Capacity',
            'issue': f"Single agents successfully handle up to {max_tokens:,} tokens",
            'tasks': None,
            'action': f'Update meta-prompt with: "Single agents can handle up to ~{max_tokens//1000}k tokens (avg: {avg_tokens//1000:.0f}k)"',
            'impact': 'Better calibration of the 8k threshold'
        })
    
    return recommendations


def generate_meta_prompt_update(results, token_analysis, recommendations):
    """Generate updated guidance for meta-prompt"""
    
    update = ["# Calibration-Based Meta-Prompt Update\n\n"]
    update.append("*Based on actual single-agent execution with extended thinking*\n\n")
    
    update.append("## Actual Performance Data\n\n")
    update.append("### Tasks Successfully Handled by Single Agent\n\n")
    update.append("| Task | Output Tokens | Notes |\n")
    update.append("|------|---------------|-------|\n")
    
    for r in results:
        if r.get('success') and not r['truncated']:
            update.append(f"| {r['task_name']} | {r['actual_output_tokens']:,} | "
                         f"{'✓ Confirmed' if 'CONFIRMED' in r.get('ground_truth_validation', '') else '⚠️  Questionable'} |\n")
    
    update.append("\n### Tasks That Require Decomposition\n\n")
    update.append("| Task | Output Tokens | Reason |\n")
    update.append("|------|---------------|--------|\n")
    
    for r in results:
        if r.get('success') and r['truncated']:
            update.append(f"| {r['task_name']} | {r['actual_output_tokens']:,} (truncated) | "
                         f"Exceeded 16k token limit |\n")
    
    update.append("\n## Key Findings for Meta-Prompt\n\n")
    
    # Calculate actual ranges
    single_agent_success = [r for r in results if r.get('success') and not r['truncated']]
    if single_agent_success:
        tokens = [r['actual_output_tokens'] for r in single_agent_success]
        update.append(f"**Single Agent Capacity**: {min(tokens):,} - {max(tokens):,} tokens\n")
        update.append(f"**Average**: {sum(tokens)//len(tokens):,} tokens\n\n")
    
    # Token estimation accuracy
    accurate = [t for t in token_analysis if t['within_range'] == True]
    evaluable = [t for t in token_analysis if t['within_range'] is not None]
    if evaluable:
        accuracy_pct = len(accurate) / len(evaluable) * 100
        update.append(f"**Token Estimation Accuracy**: {accuracy_pct:.0f}% within predicted range\n\n")
    else:
        update.append("**Token Estimation Accuracy**: No predictions available for comparison\n\n")
    
    update.append("## Recommendations\n\n")
    
    for rec in recommendations:
        priority_emoji = {'CRITICAL': '🔴', 'HIGH': '🟡', 'MEDIUM': '🟠', 'INFO': 'ℹ️'}.get(rec['priority'], '•')
        update.append(f"{priority_emoji} **{rec['priority']}**: {rec['category']}\n")
        update.append(f"- Issue: {rec['issue']}\n")
        if rec['tasks']:
            update.append(f"- Tasks: {', '.join(rec['tasks'])}\n")
        update.append(f"- Action: {rec['action']}\n")
        update.append(f"- Impact: {rec['impact']}\n\n")
    
    update.append("## Suggested Meta-Prompt Improvements\n\n")
    update.append("```\n")
    update.append("# Calibrated Token Thresholds (from actual data):\n\n")
    
    if single_agent_success:
        max_success = max(r['actual_output_tokens'] for r in single_agent_success)
        update.append(f"- Single agents reliably handle up to {max_success:,} tokens\n")
        update.append(f"- Consider DECOMPOSE when estimated output > {max_success//1000}k tokens\n")
    
    update.append("\n# Real Examples to Include:\n\n")
    for r in results:
        if r.get('success'):
            update.append(f"- {r['task_name']}: {r['actual_output_tokens']:,} tokens "
                         f"({'SINGLE_AGENT' if not r['truncated'] else 'DECOMPOSE required'})\n")
    
    update.append("```\n")
    
    return "".join(update)


def main():
    print("\n📊 Analyzing calibration data...\n")
    
    results = load_calibration_results()
    if not results:
        return
    
    print(f"Loaded {len(results)} calibration runs")
    
    predictions = load_meta_prompt_predictions()
    if predictions:
        print(f"Loaded {len(predictions)} meta-prompt predictions\n")
    else:
        print("No meta-prompt predictions found (comparison will be limited)\n")
    
    print("=" * 60)
    print("GROUND TRUTH VALIDATION")
    print("=" * 60)
    
    gt_analysis = analyze_ground_truth_accuracy(results)
    
    print(f"\n✓ Confirmed: {len(gt_analysis['confirmed'])}")
    for r in gt_analysis['confirmed']:
        print(f"  - {r['task_name']}: {r['actual_output_tokens']:,} tokens")
    
    if gt_analysis['questionable']:
        print(f"\n⚠️  Questionable: {len(gt_analysis['questionable'])}")
        for r in gt_analysis['questionable']:
            print(f"  - {r['task_name']}: {r['actual_output_tokens']:,} tokens")
            print(f"    {r['ground_truth_validation']}")
    
    if gt_analysis['failed']:
        print(f"\n❌ Failed: {len(gt_analysis['failed'])}")
        for r in gt_analysis['failed']:
            print(f"  - {r['task_name']}: {r['actual_output_tokens']:,} tokens (TRUNCATED)")
            print(f"    {r['ground_truth_validation']}")
    
    # Token estimation analysis
    if predictions:
        print("\n" + "=" * 60)
        print("TOKEN ESTIMATION ACCURACY")
        print("=" * 60)
        
        token_analysis = analyze_token_estimation_accuracy(results, predictions)
        
        for t in token_analysis:
            status = "✓" if t['within_range'] else "❌" if t['within_range'] is not None else "?"
            print(f"\n{status} {t['task']}")
            print(f"  Estimated: {t['estimated']} | Actual: {t['actual']:,}")
            if t['error'] != 0:
                print(f"  Error: {t['error']:+,} tokens ({t['error_pct']:+.1f}%)")
    else:
        token_analysis = []
    
    # Generate recommendations
    recommendations = generate_meta_prompt_recommendations(results, predictions, token_analysis)
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS FOR META-PROMPT")
    print("=" * 60)
    
    for rec in recommendations:
        print(f"\n{rec['priority']}: {rec['category']}")
        print(f"  {rec['issue']}")
        print(f"  → {rec['action']}")
    
    # Generate meta-prompt update
    meta_update = generate_meta_prompt_update(results, token_analysis, recommendations)
    
    output_path = Path("calibration_output/meta_prompt_update.md")
    with open(output_path, "w") as f:
        f.write(meta_update)
    
    print(f"\n✅ Analysis complete!")
    print(f"📝 Meta-prompt update saved to: {output_path}")


if __name__ == "__main__":
    main()
