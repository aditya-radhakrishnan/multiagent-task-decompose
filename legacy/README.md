# Legacy: original multiagent_poc

Earlier scripts and outputs that led to the current framework in `src/`. Kept for reference and reproducibility.

- `auto_orchestrator.py`, `auto_comparison.py`: original auto-decomposition and 2-task head-to-head (subtask cap may be 8k in older runs)
- `calibration_*`, `meta_prompt_*`: meta-prompt routing (SINGLE_AGENT vs DECOMPOSE) calibration
- `*_output/`: results from the first experiments (API endpoint and e-commerce comparisons, calibration runs)
- `batch_runner.py`, `statistical_analyzer.py`, `task_generator.py`: earlier batch/statistical validation tooling
