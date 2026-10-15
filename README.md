# Code and data: Attributing and Budgeting the Cost of Agentic AI Under Stated Uncertainty

[![DOI](https://zenodo.org/badge/1420179673.svg)](https://doi.org/10.5281/zenodo.23384893)

This package reproduces the numerical results in the paper: the budget-coverage pilot (E1, E1c) on public agent traces and the illustrative case study. Everything is deterministic (seed 20261004).

Author: Xiaochao Pu (xcpu@umich.edu). Version 1.0.0. Code: MIT. Data tables: CC BY 4.0 (see `LICENSE`).

## Contents

| Path | Purpose |
|---|---|
| `code/eval_budget_coverage.py` | E1: coverage of four batch budgets (mean, normal, resampled quantile, two-level bootstrap) at the 80% and 90% levels, stable and shifted splits, split-conformal per-task cap |
| `code/eval_recalibration.py` | E1c (post hoc): pooled versus recent-only recalibration after a shift |
| `code/casestudy_simulation.py` | Section VI simulation (200,000 draws) and its sensitivity table |
| `code/summarize.py` | Prints every pilot number quoted in the paper from the result files |
| `code/hal_stream_extract.py`, `code/hal_calls_to_csv.py` | Convert encrypted HAL USACO traces to per-task cost tables (streaming, low memory) |
| `code/hal_decrypt_json.py`, `code/hal_to_csv.py` | Same for the small SWE-bench Verified Mini traces |
| `data/*_per_task.csv`, `data/e1*_input_*.csv` | Per-task costs at list prices (one row per task and model) |
| `data/e1*_results_*.json`, `data/e1c_recal_*.json` | Released results |
| `data/PROVENANCE.md` | Source files, run IDs and SHA-256 hashes of the HAL downloads |
| `run_all.sh` | Regenerates all results and checks them against the released files |

## Reproduce the results

```
pip install numpy==2.2.6 pandas==2.3.3
bash run_all.sh            # under a minute; writes to ./out and compares with data/
cat out/summary.txt        # the numbers quoted in the paper
```

`run_all.sh` exits with an error if any regenerated result file differs from the released one. The ijson and cryptography packages are needed only to rebuild the CSVs from the original traces.

## Input format

One row per task and model: `task_id, run_id, cost_usd, group` plus informational columns. `group` is the difficulty level (USACO) or repository (SWE-bench). The shifted split calibrates on the cheaper half of the groups, ranked by mean cost, and tests on the costlier half. Splits are by task, never by run.

## Rebuild the per-task tables from the original traces (optional)

The HAL traces are large and are not redistributed here. Download them from the leaderboard pages listed in `data/PROVENANCE.md`, decrypt using HAL's published procedure, then:

```
python code/hal_stream_extract.py <file>.json.encrypted /tmp/usaco     # per-call records
python code/hal_calls_to_csv.py hal_usaco_per_task.csv <stem> ...      # per-task costs
python code/hal_to_csv.py hal_swebench_mini_per_task.csv <decrypted>.json ...
```

Cost rules: only the outer `litellm` span of each call is counted, because HAL logs some calls twice; Anthropic cache-read and cache-write tokens are priced at 0.1 and 1.25 times the input price; prices are the dated list prices in the scripts.

## Known limits

One run per task, so run-to-run variance is not tested. SWE-bench Opus 4.1 costs are censored by a $4 per-instance limit. The recalibration test (E1c) was not pre-specified. See the paper's evaluation section.
