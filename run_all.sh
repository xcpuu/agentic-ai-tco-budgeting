#!/usr/bin/env bash
# Regenerates every number in the pilot section of Paper A from the per-task CSVs in data/.
# Usage: bash run_all.sh [output_dir]      (under a minute on a laptop; fixed seed 20261004)
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-out}"; mkdir -p "$OUT"
PY="${PYTHON:-python3}"
for m in gemini20flash deepseekv3 gpt41 sonnet37; do
  $PY code/eval_budget_coverage.py --csv data/e1_usaco_input_$m.csv --group-col group --out "$OUT/e1_usaco_results_$m.json" > /dev/null
  $PY code/eval_recalibration.py data/e1_usaco_input_$m.csv "$OUT/e1c_recal_$m.json" > /dev/null
done
for m in gemini20flash deepseekv3 opus41; do
  $PY code/eval_budget_coverage.py --csv data/e1_input_$m.csv --group-col group --out "$OUT/e1_results_$m.json" > /dev/null
done
$PY code/casestudy_simulation.py > "$OUT/casestudy_output.txt"
cp data/hal_usaco_per_task.csv data/hal_swebench_mini_per_task.csv "$OUT/"
$PY code/summarize.py "$OUT" > "$OUT/summary.txt"
# Compare regenerated results with the released ones
$PY - "$OUT" <<'PY'
import json, glob, os, sys
out = sys.argv[1]; bad = 0
for f in sorted(glob.glob(out + "/e1*_results_*.json") + glob.glob(out + "/e1c_recal_*.json")):
    g = os.path.join("data", os.path.basename(f))
    a, b = json.load(open(f)), json.load(open(g))
    a, b = (a.get("results", a), b.get("results", b)) if isinstance(a, dict) else (a, b)
    same = a == b; bad += (not same)
    print(("OK    " if same else "DIFF  ") + os.path.basename(f))
sys.exit(1 if bad else 0)
PY
echo "Done. See $OUT/summary.txt and $OUT/casestudy_output.txt"
