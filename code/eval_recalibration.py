#!/usr/bin/env python3
"""E1c (post hoc, not pre-specified): effect of recalibrating after a shift in task mix.
Calibrate on cheaper groups; the k newest tasks come from the costlier groups; test on the
remaining costlier tasks. Modes: pooled (old + k new) and recent_only (the k new tasks only).
20 random draws per k. Usage: eval_recalibration.py in.csv out.json"""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_budget_coverage import Pool, resampled_quantile, SEED
df = pd.read_csv(sys.argv[1])
rng = np.random.default_rng(SEED)
gm = df.groupby("group")["cost_usd"].mean().sort_values()
order = list(gm.index); hi = set(order[len(order)//2:])
low = df[~df.group.isin(hi)]; high = df[df.group.isin(hi)]
hi_ids = high.task_id.unique()
out = []
for mode, ks in (("pooled", (0, 10, 20, 40)), ("recent_only", (20, 40))):
    for k in ks:
        covs = {10: [], 100: []}
        for rep in range(20):
            pick = set(rng.choice(hi_ids, size=k, replace=False)) if k else set()
            new = high[high.task_id.isin(pick)]
            cal = pd.concat([low, new]) if mode == "pooled" else new
            test = high[~high.task_id.isin(pick)]
            pc, pt = Pool(cal), Pool(test)
            for n in (10, 100):
                b = resampled_quantile(pc, n, rng, B=1000, level=0.90, two_level=True)
                covs[n].append(float((pt.batches(n, 1000, rng) <= b).mean()))
        for n in (10, 100):
            out.append(dict(mode=mode, k=k, n=n, coverage=round(float(np.mean(covs[n])), 3),
                            sd=round(float(np.std(covs[n])), 3), test_tasks=int(len(hi_ids) - k)))
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(sys.argv[1].split("input_")[1], [(o["mode"][:3], o["k"], o["n"], o["coverage"]) for o in out if o["mode"]=="recent_only" or o["k"] in (0,40)])
