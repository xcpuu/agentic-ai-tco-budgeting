#!/usr/bin/env python3
"""Per-task cost CSV from the call records written by hal_stream_extract.py (USACO traces).

Counting rule: one record per model call. HAL logs some calls twice (an inner provider span
nested under an outer litellm span); we keep only the OUTER span ('litellm.*') and use the
provider-reported usage in the span summary when present, else the output usage. Cost =
tokens x LIST PRICE (assumption, dated to the 2025 runs). The prices below reproduce HAL's
own reported total_cost when applied to HAL's reported (double-counted) usage, which is how
they were checked.

Usage: hal_calls_to_csv.py out.csv stem1 [stem2 ...]   (stems of files in /tmp/usaco)
"""
import csv, json, sys, collections

PRICES = {  # USD per million tokens (input, output)
    "deepseek-ai/DeepSeek-V3": (1.25, 1.25),
    "gpt-4.1-2025-04-14": (2.00, 8.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "claude-3-7-sonnet-20250219": (3.00, 15.00),
}


def convert(stem, d="/tmp/usaco"):
    meta = json.load(open(f"{d}/{stem}.meta.json"))
    mk = next(iter(meta["total_usage"]))
    p_in, p_out = PRICES[mk]
    solved = set(meta["results"]["successful_tasks"])
    per = collections.defaultdict(lambda: [0, 0, 0])
    n_all = collections.Counter()
    for line in open(f"{d}/{stem}.calls.jsonl"):
        c = json.loads(line)
        n_all[c["op"]] += 1
        if not c["op"].startswith("litellm."):
            continue
        pt = c["sum_prompt"] or c["prompt_tokens"]
        ct = c["sum_completion"] or c["completion_tokens"]
        a = per[c["task"]]
        a[0] += pt; a[1] += ct; a[2] += 1
    rows = []
    for t, (pt, ct, n) in per.items():
        grp = t.split("_")[1] if "_" in t else "unknown"
        rows.append(dict(model=mk, task_id=t, run_id=0, cost_usd=(pt * p_in + ct * p_out) / 1e6,
                         input_tokens=pt, output_tokens=ct, calls=n, resolved=int(t in solved), group=grp))
    rep = meta["total_usage"][mk]
    val = dict(model=mk, tasks=len(rows), unique_in=sum(r["input_tokens"] for r in rows),
               unique_out=sum(r["output_tokens"] for r in rows), reported_in=rep["prompt_tokens"],
               reported_out=rep["completion_tokens"], hal_total_cost=meta["results"]["total_cost"],
               recomputed_cost=sum(r["cost_usd"] for r in rows), span_ops=dict(n_all), accuracy=meta["results"]["accuracy"])
    val["reported_over_unique_in"] = round(val["reported_in"] / val["unique_in"], 3)
    return rows, val


if __name__ == "__main__":
    out, stems = sys.argv[1], sys.argv[2:]
    allrows = []
    for s in stems:
        rows, val = convert(s)
        allrows += rows
        print(json.dumps(val))
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(allrows[0].keys()))
        w.writeheader(); w.writerows(allrows)
    print("wrote", out, len(allrows), "rows")
