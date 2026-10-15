#!/usr/bin/env python3
"""Regenerates the numbers quoted in the pilot section of Paper A from the result files in ../data.
Usage: python summarize.py [data_dir]"""
import json, sys, os, itertools
import numpy as np, pandas as pd
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
U = ["gemini20flash", "deepseekv3", "gpt41", "sonnet37"]
S = ["gemini20flash", "deepseekv3", "opus41"]
NAME = dict(gemini20flash="Gemini 2.0 Flash", deepseekv3="DeepSeek V3", gpt41="GPT-4.1", sonnet37="Claude 3.7 Sonnet", opus41="Claude Opus 4.1")

def res(path):
    return pd.DataFrame(json.load(open(path))["results"])

print("== Table: USACO coverage of the nominal 90% budget (unshifted; shifted two-level) ==")
rows, caps = [], []
for m in U:
    r = res(f"{D}/e1_usaco_results_{m}.json")
    caps.append(json.load(open(f"{D}/e1_usaco_results_{m}.json"))["per_task_cap"]["heldout_coverage"])
    for n in (10, 100):
        g = lambda sc, me: r[(r.scenario == sc) & (r.method == me) & (r.n == n)].iloc[0]
        rows.append(dict(model=NAME[m], n=n, mean=g("unshifted", "mean").coverage, normal=g("unshifted", "normal@90").coverage,
                         resampled=g("unshifted", "resampled-quantile@90").coverage, two_level=g("unshifted", "two-level@90").coverage,
                         two_level_80=g("unshifted", "two-level@80").coverage, sd_two_level=g("unshifted", "two-level@90").coverage_sd,
                         width_vs_mean=g("unshifted", "two-level@90").bound_over_mean, shifted=g("shifted", "two-level@90").coverage))
t = pd.DataFrame(rows); print(t.round(3).to_string(index=False))
ok = lambda c: (t[c] - 0.90).abs() <= 0.03 + 1e-9
print("two-level within +-3 points:", int(ok("two_level").sum()), "of", len(t), "| normal:", int(ok("normal").sum()), "| resampled:", int(ok("resampled").sum()))
print("mean-based coverage range: %.3f-%.3f" % (t["mean"].min(), t["mean"].max()))
print("two-level@80 range: %.3f-%.3f; SD range %.3f-%.3f; width %.3f-%.3f" % (t.two_level_80.min(), t.two_level_80.max(), t.sd_two_level.min(), t.sd_two_level.max(), t.width_vs_mean.min(), t.width_vs_mean.max()))
for n in (10, 100):
    x = t[t.n == n].shifted; print(f"shifted two-level n={n}: {x.min():.3f}-{x.max():.3f}")
print("per-task split-conformal cap held-out coverage:", caps)

print("\n== SWE-bench Verified Mini (unshifted) ==")
for m in S:
    r = res(f"{D}/e1_results_{m}.json")
    for n in (10, 100):
        a = r[(r.scenario == "unshifted") & (r.n == n)].set_index("method")
        print(NAME[m], n, "mean %.3f two-level@90 %.3f sd %.3f width %.3f" % (a.loc["mean"].coverage, a.loc["two-level@90"].coverage, a.loc["two-level@90"].coverage_sd, a.loc["two-level@90"].bound_over_mean))

print("\n== Recalibration (post hoc), two-level@90 on remaining costlier tasks ==")
rc = pd.concat([pd.DataFrame(json.load(open(f"{D}/e1c_recal_{m}.json"))).assign(model=NAME[m]) for m in U])
for (mode, k, n), g in rc.groupby(["mode", "k", "n"]):
    print(f"{mode:12s} k={k:2d} n={n:3d}: {g.coverage.min():.3f}-{g.coverage.max():.3f}  (test tasks {int(g.test_tasks.iloc[0])})")

print("\n== Per-task cost shape and cross-model rank correlation ==")
for name, f, models in (("USACO", "hal_usaco_per_task.csv", None), ("SWE-bench", "hal_swebench_mini_per_task.csv", None)):
    d = pd.read_csv(f"{D}/{f}")
    for mk, g in d.groupby("model"):
        c = g.cost_usd; print(name, mk, "p90/p50 %.2f max/median %.2f frac>=3.90: %.2f" % (np.percentile(c, 90) / np.percentile(c, 50), c.max() / c.median(), (c >= 3.9).mean()))
    w = d.pivot_table(index="task_id", columns="model", values="cost_usd").dropna()
    sp = w.corr(method="spearman").values; iu = np.triu_indices_from(sp, 1)
    print(name, "cross-model Spearman: %.2f-%.2f (%d tasks in common)" % (sp[iu].min(), sp[iu].max(), len(w)))
