# Multi-Agent Task Decomposition Research

When should a software task go to a single agent vs a parallel multi-agent (auto-decomposition) system?
Compares **single agent**, **parallel multi-agent**, and **best-of-N at equal token budget** on 5 tasks,
graded with a task-agnostic 12-item binary checklist.

## Layout
```
tasks.json                       5 task definitions
src/run_experiments.py           Stage 1: run tasks -> experiments/outputs/<task>/<approach>.json
src/evaluate_experiments.py      Stage 2: grade outputs -> experiments/evaluations/<version>/<task>.json
src/visualize_experiments.py     Stage 3: tables + charts -> experiments/visualizations/<version>/report.{html,md}
src/auto_orchestrator.py         Parallel multi-agent orchestrator (subtask cap raised 8k -> 16k)
src/graders/binary_checklist.py  Universal checklist grader
```

## Usage
```bash
pip install -r requirements.txt && export ANTHROPIC_API_KEY=...
python src/run_experiments.py --tasks all --approaches all     # expensive; skips finished runs
python src/run_experiments.py --tasks auth_system --overwrite  # replace one task only
python src/evaluate_experiments.py                              # cheap; re-run after changing grader
python src/evaluate_experiments.py --tasks ecommerce --overwrite
python src/visualize_experiments.py                             # free
```
Best-of-N runs after parallel for each task so N = parallel total tokens / 12,000.
Run `--approaches single,parallel` first on a task, then `best-of-n`, if you want to control order.

## Notes
- Change the grader: add a module in `src/graders/`, run evaluate with `--grader <name> --version <label>`; old evaluations are kept.
- Grader sees up to 120,000 characters of output (the earlier 10,000 cut-off would have biased against long multi-agent outputs).
- Parallel output graded = all subtask state files concatenated.
- Best-of-N attempts run sequentially, so its time is the sum of attempts (a parallel version would be faster).
