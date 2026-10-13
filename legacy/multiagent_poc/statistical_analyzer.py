"""
Statistical analysis of batch experiment results
"""

import json
import os
from typing import Dict, List
import statistics

class StatisticalAnalyzer:
    """Analyze batch experiment results with statistical tests"""
    
    def __init__(self, results_file: str = "./batch_results/batch_results.json"):
        self.results_file = results_file
        self.results = self.load_results()
    
    def load_results(self) -> List[Dict]:
        """Load batch results from JSON"""
        with open(self.results_file, 'r') as f:
            data = json.load(f)
        return data["results"]
    
    def compute_summary_stats(self):
        """Compute summary statistics for each approach and complexity"""
        stats = {
            "simple": {"single_agent": [], "auto_decomposition": []},
            "medium": {"single_agent": [], "auto_decomposition": []},
            "complex": {"single_agent": [], "auto_decomposition": []}
        }
        
        # Collect data
        for result in self.results:
            complexity = result["complexity"]
            
            stats[complexity]["single_agent"].append({
                "quality": result["evaluation"]["single_agent"]["total"],
                "cost": result["single_agent"]["cost_usd"],
                "completion_pct": result["evaluation"]["single_agent"]["completion_pct"],
                "tokens": result["single_agent"]["total_tokens"]
            })
            
            stats[complexity]["auto_decomposition"].append({
                "quality": result["evaluation"]["auto_decomposition"]["total"],
                "cost": result["auto_decomposition"]["cost_usd"],
                "completion_pct": result["evaluation"]["auto_decomposition"]["completion_pct"],
                "tokens": result["auto_decomposition"]["total_tokens"],
                "num_subtasks": result["auto_decomposition"]["num_subtasks"]
            })
        
        return stats
    
    def print_summary_table(self):
        """Print formatted summary statistics"""
        stats = self.compute_summary_stats()
        
        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        
        for complexity in ["simple", "medium", "complex"]:
            print(f"\n{complexity.upper()} TASKS")
            print("-"*80)
            
            for approach in ["single_agent", "auto_decomposition"]:
                data = stats[complexity][approach]
                
                if not data:
                    continue
                
                qualities = [d["quality"] for d in data]
                costs = [d["cost"] for d in data]
                completions = [d["completion_pct"] for d in data]
                
                print(f"\n{approach.replace('_', ' ').title()}:")
                print(f"  Quality Score:    {statistics.mean(qualities):.2f} ± {statistics.stdev(qualities) if len(qualities) > 1 else 0:.2f}")
                print(f"  Cost (USD):       ${statistics.mean(costs):.4f} ± ${statistics.stdev(costs) if len(costs) > 1 else 0:.4f}")
                print(f"  Completion (%):   {statistics.mean(completions):.1f}% ± {statistics.stdev(completions) if len(completions) > 1 else 0:.1f}%")
                
                if approach == "auto_decomposition":
                    subtasks = [d["num_subtasks"] for d in data]
                    print(f"  Avg Subtasks:     {statistics.mean(subtasks):.1f}")
    
    def compute_t_test(self, complexity: str, metric: str):
        """Compute t-test for difference between approaches"""
        stats = self.compute_summary_stats()
        
        single_data = [d[metric] for d in stats[complexity]["single_agent"]]
        auto_data = [d[metric] for d in stats[complexity]["auto_decomposition"]]
        
        if len(single_data) < 2 or len(auto_data) < 2:
            return None, None, "Insufficient data"
        
        # Simple two-sample t-test (using basic implementation)
        mean_diff = statistics.mean(auto_data) - statistics.mean(single_data)
        
        # Cohen's d (effect size)
        pooled_std = ((statistics.stdev(single_data)**2 + statistics.stdev(auto_data)**2) / 2) ** 0.5
        if pooled_std > 0:
            cohens_d = mean_diff / pooled_std
        else:
            cohens_d = 0
        
        return mean_diff, cohens_d, "computed"
    
    def print_statistical_tests(self):
        """Print results of statistical tests"""
        print("\n" + "="*80)
        print("STATISTICAL TESTS")
        print("="*80)
        
        for complexity in ["simple", "medium", "complex"]:
            print(f"\n{complexity.upper()} TASKS")
            print("-"*80)
            
            for metric, name in [("quality", "Quality Score"), ("cost", "Cost"), ("completion_pct", "Completion %")]:
                mean_diff, cohens_d, status = self.compute_t_test(complexity, metric)
                
                if status != "computed":
                    print(f"{name}: {status}")
                    continue
                
                direction = "higher" if mean_diff > 0 else "lower"
                effect = "small" if abs(cohens_d) < 0.5 else "medium" if abs(cohens_d) < 0.8 else "large"
                
                print(f"\n{name}:")
                print(f"  Mean difference: {mean_diff:+.2f} (auto-decomp {direction})")
                print(f"  Effect size (Cohen's d): {cohens_d:.2f} ({effect} effect)")
    
    def compute_win_rates(self):
        """Compute win rates by complexity"""
        wins = {
            "simple": {"single_agent": 0, "auto_decomposition": 0, "tie": 0},
            "medium": {"single_agent": 0, "auto_decomposition": 0, "tie": 0},
            "complex": {"single_agent": 0, "auto_decomposition": 0, "tie": 0}
        }
        
        for result in self.results:
            complexity = result["complexity"]
            winner = result["evaluation"]["winner"]
            wins[complexity][winner] += 1
        
        return wins
    
    def print_win_rates(self):
        """Print win rate analysis"""
        wins = self.compute_win_rates()
        
        print("\n" + "="*80)
        print("WIN RATES (By Quality Score)")
        print("="*80)
        
        for complexity in ["simple", "medium", "complex"]:
            total = sum(wins[complexity].values())
            if total == 0:
                continue
            
            print(f"\n{complexity.upper()} TASKS (n={total})")
            print("-"*80)
            
            for approach in ["single_agent", "auto_decomposition", "tie"]:
                count = wins[complexity][approach]
                pct = (count / total * 100) if total > 0 else 0
                print(f"  {approach.replace('_', ' ').title()}: {count}/{total} ({pct:.1f}%)")
    
    def generate_report(self, output_file: str = "./batch_results/statistical_report.md"):
        """Generate markdown report with all statistics"""
        stats = self.compute_summary_stats()
        wins = self.compute_win_rates()
        
        with open(output_file, 'w') as f:
            f.write("# Statistical Analysis Report\n\n")
            f.write(f"Total Experiments: {len(self.results)}\n\n")
            
            # Summary table
            f.write("## Summary Statistics\n\n")
            
            for complexity in ["simple", "medium", "complex"]:
                f.write(f"### {complexity.upper()} Tasks\n\n")
                f.write("| Metric | Single Agent | Auto-Decomposition |\n")
                f.write("|--------|--------------|--------------------|\n")
                
                single_data = stats[complexity]["single_agent"]
                auto_data = stats[complexity]["auto_decomposition"]
                
                if single_data and auto_data:
                    qualities_s = [d["quality"] for d in single_data]
                    qualities_a = [d["quality"] for d in auto_data]
                    costs_s = [d["cost"] for d in single_data]
                    costs_a = [d["cost"] for d in auto_data]
                    comp_s = [d["completion_pct"] for d in single_data]
                    comp_a = [d["completion_pct"] for d in auto_data]
                    
                    f.write(f"| Quality Score | {statistics.mean(qualities_s):.2f} ± {statistics.stdev(qualities_s) if len(qualities_s) > 1 else 0:.2f} | {statistics.mean(qualities_a):.2f} ± {statistics.stdev(qualities_a) if len(qualities_a) > 1 else 0:.2f} |\n")
                    f.write(f"| Cost (USD) | ${statistics.mean(costs_s):.4f} | ${statistics.mean(costs_a):.4f} |\n")
                    f.write(f"| Completion (%) | {statistics.mean(comp_s):.1f}% | {statistics.mean(comp_a):.1f}% |\n")
                    
                    if auto_data:
                        subtasks = [d["num_subtasks"] for d in auto_data]
                        f.write(f"| Avg Subtasks | - | {statistics.mean(subtasks):.1f} |\n")
                
                f.write("\n")
            
            # Win rates
            f.write("## Win Rates\n\n")
            for complexity in ["simple", "medium", "complex"]:
                total = sum(wins[complexity].values())
                if total > 0:
                    f.write(f"### {complexity.upper()} (n={total})\n")
                    for approach in ["single_agent", "auto_decomposition", "tie"]:
                        count = wins[complexity][approach]
                        pct = (count / total * 100)
                        f.write(f"- {approach.replace('_', ' ').title()}: {count}/{total} ({pct:.1f}%)\n")
                    f.write("\n")
            
            # Effect sizes
            f.write("## Effect Sizes (Cohen's d)\n\n")
            for complexity in ["simple", "medium", "complex"]:
                f.write(f"### {complexity.upper()}\n")
                for metric, name in [("quality", "Quality"), ("cost", "Cost"), ("completion_pct", "Completion")]:
                    mean_diff, cohens_d, status = self.compute_t_test(complexity, metric)
                    if status == "computed":
                        effect = "small" if abs(cohens_d) < 0.5 else "medium" if abs(cohens_d) < 0.8 else "large"
                        f.write(f"- {name}: d={cohens_d:.2f} ({effect} effect)\n")
                f.write("\n")
        
        print(
