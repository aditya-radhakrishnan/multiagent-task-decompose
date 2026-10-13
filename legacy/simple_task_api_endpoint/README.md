# Simple task (API endpoint: GET /api/user/preferences)

Only the comparison report and summary survive (34/40 single vs 38/40 auto-decomposition; 7,452 vs 13,555 tokens; $0.1101 vs $0.1367).
The raw single-agent output and subtask state files for this run were overwritten when the e-commerce comparison reused the same
`auto_comparison_output/` and `auto_poc_output/` folders. The new framework (`experiments/outputs/<task>/`) keeps each task separate.
