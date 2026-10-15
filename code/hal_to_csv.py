#!/usr/bin/env python3
"""Convert decrypted HAL SWE-bench Verified Mini traces to a per-task cost CSV.

One row per (model, task). Tokens come from the litellm.completion records only,
because HAL logs each call twice in some files (an inner openai/anthropic record
nested under the litellm record); counting both doubles the tokens.
Cost = tokens x LIST PRICE (dated, see PRICES). Anthropic cache pricing follows
the published multipliers (read 0.1x, write 1.25x input).  Prices are
assumptions stated in the paper, not values read from the traces, except that
for DeepSeek V3 and Gemini 2.0 Flash they reproduce HAL's own total_cost.

Usage: hal_to_csv.py out.csv trace1.json trace2.json ...
"""
import json, sys, csv, collections

PRICES = {  # USD per million tokens (input, output); price date: runs of Apr-Aug 2025
    "deepseek-ai/DeepSeek-V3": (1.25, 1.25),          # Together AI list; reproduces HAL cost
    "gemini-2.0-flash": (0.10, 0.40),                  # Google list; reproduces HAL cost
    "claude-opus-4-1-20250805": (15.0, 75.0),          # Anthropic list; cache read 0.1x, write 1.25x
}


def model_key(d):
    return next(iter(d["total_usage"].keys()))


def convert(path):
    d = json.load(open(path))
    mk = model_key(d)
    p_in, p_out = PRICES[mk]
    anth = mk.startswith("claude")
    solved = set(d["results"]["successful_tasks"])
    per = collections.defaultdict(lambda: dict(inp=0, out=0, cr=0, cw=0, calls=0))
    for r in d["raw_logging_results"]:
        if not r["op_name"].split("/")[-1].startswith("litellm.completion"):
            continue
        o = r.get("output")
        if not isinstance(o, dict) or not o.get("usage"):
            continue
        u = o["usage"]
        t = r.get("weave_task_id") or r["attributes"].get("weave_task_id")
        a = per[t]
        a["inp"] += u.get("prompt_tokens") or 0
        a["out"] += u.get("completion_tokens") or 0
        a["cr"] += u.get("cache_read_input_tokens") or 0
        a["cw"] += u.get("cache_creation_input_tokens") or 0
        a["calls"] += 1
    rows = []
    for t, a in per.items():
        if t is None:
            continue
        if anth:
            fresh = max(a["inp"] - a["cr"], 0)  # cache-creation tokens are reported separately from prompt_tokens in these files
            cost = (fresh * p_in + a["cr"] * 0.1 * p_in + a["cw"] * 1.25 * p_in + a["out"] * p_out) / 1e6
        else:
            cost = (a["inp"] * p_in + a["out"] * p_out) / 1e6
        repo = t.split("__")[0] + "/" + t.split("__")[1].rsplit("-", 1)[0] if "__" in t else "unknown"
        rows.append(dict(model=mk, task_id=t, run_id=0, cost_usd=cost, input_tokens=a["inp"],
                         output_tokens=a["out"], cache_read=a["cr"], cache_write=a["cw"], calls=a["calls"],
                         resolved=int(t in solved), group=repo))
    # validation against HAL's own reported totals
    tot_tok_in = sum(r["input_tokens"] for r in rows)
    tot_tok_out = sum(r["output_tokens"] for r in rows)
    rep = d["total_usage"][mk]
    val = dict(model=mk, tasks=len(rows), unique_in=tot_tok_in, reported_in=rep["prompt_tokens"],
               unique_out=tot_tok_out, reported_out=rep["completion_tokens"],
               hal_total_cost=d["total_cost"], recomputed_cost=sum(r["cost_usd"] for r in rows))
    return rows, val


if __name__ == "__main__":
    out, files = sys.argv[1], sys.argv[2:]
    allrows = []
    for f in files:
        rows, val = convert(f)
        allrows += rows
        print(json.dumps(val))
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(allrows[0].keys()))
        w.writeheader()
        w.writerows(allrows)
    print("wrote", out, len(allrows), "rows")
