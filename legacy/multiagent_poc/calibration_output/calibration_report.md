# Calibration Results - Ground Truth Validation

## Purpose
This calibration validates the ground truth labels by running single agents with extended thinking on each task. Tasks marked SINGLE_AGENT should complete without truncation. Tasks marked DECOMPOSE may truncate or be very large.

## Summary

| Task | Ground Truth | Output Tokens | Truncated | Validation |
|------|--------------|---------------|-----------|------------|

## Detailed Analysis

### ❌ Failed Ground Truth (1)

**E-commerce Catalog** (complex_1)
- Ground truth: SINGLE_AGENT
- Output tokens: 12,000
- FAILED - Expected SINGLE_AGENT to work, but truncated
- **Action**: Ground truth should be changed to DECOMPOSE

## Cost Summary

Total calibration cost: $0.0000

