#!/usr/bin/env python3
"""
E1: Retrospective evaluation of budget coverage on agent-run cost data.

Question (RQ3): do distribution-aware budget bounds for a batch of n tasks
achieve their nominal coverage better than a mean-based budget?

Input CSV columns (one row per agent run):
  task_id, run_id, cost_usd [, model] [, resolved (0/1)] [, group]
  'group' = repository / task family; used to build a shifted test set.
Real data: Bai et al. (arXiv:2604.22750) trajectories or HAL traces, converted
to this schema (see README section at the bottom). Until real data is supplied,
run with --synthetic, which is a SCHEMA/PIPELINE TEST ONLY; its numbers are
not evidence about any real system and must never be quoted as results.

Forecasts of the total cost of a future batch of n tasks (90% upper bound):
  mean    : n * mean(calibration cost)
  normal  : n*mean + z90 * sd * sqrt(n)         (iid normal approximation)
  quantile: finite-sample-corrected 90% quantile of resampled calibration
            batch totals (distribution-aware, no shape assumption).
            Called 'resampled-quantile', not conformal: batches are resampled
            from the calibration pool, so exchangeability guarantees are
            approximate. Per-task caps use a true split-conformal quantile.
Metrics per (method, n, scenario): coverage of the bound, over-budget rate for
the mean forecast, mean relative excess when exceeded, relative bound width.
"""
import argparse, json, math
import numpy as np
import pandas as pd

SEED = 20261004
Z90 = 1.2815515655446004
Z80 = 0.8416212335729143
LEVELS = ((0.80, Z80), (0.90, Z90))


def synthetic(rng, n_tasks=500, n_runs=4, n_groups=12):
    """Pipeline test data: grouped lognormal task medians, run-level noise."""
    grp = rng.integers(0, n_groups, n_tasks)
    g_scale = rng.lognormal(0, 0.5, n_groups)
    med = 1.2 * g_scale[grp] * rng.lognormal(0, 0.8, n_tasks)
    rows = []
    for t in range(n_tasks):
        for r in range(n_runs):
            rows.append((f"t{t}", r, float(med[t] * rng.lognormal(0, 0.7)),
                         int(rng.random() < 0.6), f"g{grp[t]}"))
    return pd.DataFrame(rows, columns=["task_id", "run_id", "cost_usd",
                                       "resolved", "group"])


def split_tasks(df, rng, frac=0.5, shift=False):
    """Calibration/test split by TASK (never by run). With shift=True the test
    set is the most expensive groups by mean cost (a different task mix)."""
    tasks = df.drop_duplicates("task_id")[["task_id", "group"]]
    if shift and tasks["group"].nunique() > 3:
        gmean = df.groupby("group")["cost_usd"].mean().sort_values()
        order = list(gmean.index)
        cut = int(len(order) * (1 - frac))
        test_g = set(order[cut:])
        test = tasks[tasks["group"].isin(test_g)]["task_id"]
        cal = tasks[~tasks["group"].isin(test_g)]["task_id"]
    else:
        ids = tasks["task_id"].to_numpy()
        rng.shuffle(ids)
        k = int(len(ids) * frac)
        cal, test = ids[:k], ids[k:]
    return df[df.task_id.isin(set(cal))], df[df.task_id.isin(set(test))]


class Pool:
    """Tasks x runs matrix (NaN-padded) for fast vectorised batch sampling."""
    def __init__(self, df):
        g = df.groupby("task_id")["cost_usd"].apply(np.array)
        self.k = np.array([len(v) for v in g])
        self.M = np.full((len(g), self.k.max()), np.nan)
        for i, v in enumerate(g):
            self.M[i, :len(v)] = v
        self.T = len(g)

    def batches(self, n, B, rng):
        """B batch totals: n tasks with replacement, one random run each."""
        ti = rng.integers(0, self.T, size=(B, n))
        ri = (rng.random((B, n)) * self.k[ti]).astype(int)
        return self.M[ti, ri].sum(axis=1)


    def batches_two_level(self, n, B, rng):
        """Two-level: each batch first bootstraps the task pool (captures the
        deployment-level uncertainty of a finite calibration sample), then
        draws n tasks from that pool."""
        boot = rng.integers(0, self.T, size=(B, self.T))
        pos = rng.integers(0, self.T, size=(B, n))
        ti = np.take_along_axis(boot, pos, axis=1)
        ri = (rng.random((B, n)) * self.k[ti]).astype(int)
        return self.M[ti, ri].sum(axis=1)


def resampled_quantile(pool, n, rng, B=2000, level=0.90, two_level=False):
    f = pool.batches_two_level if two_level else pool.batches
    totals = np.sort(f(n, B, rng))
    k = min(B, math.ceil((B + 1) * level))
    return float(totals[k - 1])


def evaluate(df, rng, ns=(10, 100), n_test_batches=1000, reps=20):
    out = []
    for scenario, shift in (("unshifted", False), ("shifted", True)):
        acc = {}
        for rep in range(reps):
            cal, test = split_tasks(df, rng, shift=shift)
            c = cal.cost_usd.to_numpy()
            mu, sd = c.mean(), c.std(ddof=1)
            for n in ns:
                pc, pt = Pool(cal), Pool(test)
                bounds = {"mean": n * mu}
                for lev, z in LEVELS:
                    tag = "@%d" % round(lev * 100)
                    bounds["normal" + tag] = n * mu + z * sd * math.sqrt(n)
                    bounds["resampled-quantile" + tag] = resampled_quantile(
                        pc, n, rng, B=1000, level=lev)
                    bounds["two-level" + tag] = resampled_quantile(
                        pc, n, rng, B=1000, level=lev, two_level=True)
                tot = pt.batches(n, n_test_batches, rng)
                for m, b in bounds.items():
                    cov = float((tot <= b).mean())
                    exc = tot[tot > b]
                    rel = float(((exc - b) / b).mean()) if len(exc) else 0.0
                    acc.setdefault((m, n), []).append(
                        (cov, rel, b / (n * mu)))
        for (m, n), v in acc.items():
            a = np.array(v)
            out.append(dict(scenario=scenario, method=m, n=n,
                            coverage=round(a[:, 0].mean(), 3),
                            coverage_sd=round(a[:, 0].std(), 3),
                            rel_excess_when_exceeded=round(a[:, 1].mean(), 3),
                            bound_over_mean=round(a[:, 2].mean(), 3)))
    return pd.DataFrame(out)


def per_task_cap(df, rng, level=0.90):
    """Split-conformal per-task cap: coverage of the cap on held-out tasks."""
    cal, test = split_tasks(df, rng)
    s = np.sort(cal.cost_usd.to_numpy())
    k = min(len(s), math.ceil((len(s) + 1) * level))
    cap = s[k - 1]
    return dict(cap_usd=round(float(cap), 3),
                heldout_coverage=round(float((test.cost_usd <= cap).mean()), 3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--group-col", default=None,
                    help="column used as task group for the shifted/reference-class test (e.g. repo or model)")
    ap.add_argument("--out", default="e1_results.json")
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    if a.synthetic:
        df = synthetic(rng)
        tag = "SYNTHETIC PIPELINE TEST - NOT EVIDENCE"
    else:
        df = pd.read_csv(a.csv)
        if a.group_col:
            df["group"] = df[a.group_col]
        if "group" not in df:
            df["group"] = "all"
        tag = a.csv
    res = evaluate(df, rng)
    cap = per_task_cap(df, rng)
    print(tag)
    print(res.to_string(index=False))
    print("per-task cap:", cap)
    json.dump(dict(source=tag, seed=SEED, results=res.to_dict("records"),
                   per_task_cap=cap), open(a.out, "w"), indent=1)

# README: converting real data
# - Bai et al.: one row per (task, model, run): cost_usd = sum of per-round
#   monetary cost from the usage records; group = repository; resolved from
#   the evaluation result. Run once per model (filter model) and report each.
# - HAL: decrypt traces (hal-decrypt.sh), sum per-call tokens x listed price
#   (state the price date); most agents have one run per task, so use it only
#   for the cross-model and price-change checks, not for run-level variance.
