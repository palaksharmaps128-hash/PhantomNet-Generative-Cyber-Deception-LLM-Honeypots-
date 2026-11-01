"""Compare two evaluation runs and print a markdown table.

Examples:
    python compare.py
    python compare.py A.csv B.csv --labels flash-lite flash --out evaluation/model_comparison.md
"""
import argparse
import csv
import math
import os
import statistics

BEFORE = "evaluation/results_gemini-3.1-flash-lite.csv"
AFTER = "evaluation/results_gemini-3.1-flash-lite_static.csv"

parser = argparse.ArgumentParser()
parser.add_argument("paths", nargs="*", help="two result CSV files (first, second)")
parser.add_argument("--labels", nargs=2, default=["Before", "After"])
parser.add_argument("--out", default="evaluation/comparison.md")
args = parser.parse_args()
first, second = args.paths if len(args.paths) == 2 else (BEFORE, AFTER)


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def p95(values):
    values = sorted(values)
    return values[min(len(values) - 1, math.ceil(0.95 * len(values)) - 1)]


def stats(rows):
    lat = [float(r["latency_s"]) for r in rows]
    llm = [float(r["latency_s"]) for r in rows if r["source"].startswith("llm")]
    py = [r for r in rows if r["source"] == "python"]
    ok = sum(r["realism_ok"] == "True" for r in rows)
    cls = sum(r["classifier_ok"] == "True" for r in rows)
    return {
        "Commands": str(len(rows)),
        "Answered by Python (no LLM)": f"{100 * len(py) / len(rows):.1f}%",
        "Latency mean, all commands": f"{statistics.mean(lat):.2f} s",
        "Latency p95, all commands": f"{p95(lat):.2f} s",
        "Latency mean, LLM commands": f"{statistics.mean(llm):.2f} s" if llm else "n/a",
        "Realism checks passed": f"{100 * ok / len(rows):.1f}%",
        "Classifier accuracy": f"{100 * cls / len(rows):.1f}%",
    }


b, a = stats(load(first)), stats(load(second))
l1, l2 = args.labels
lines = [
    "# Comparison",
    "",
    f"{l1}: `{first}`",
    f"{l2}: `{second}`",
    "",
    f"| Metric | {l1} | {l2} |",
    "|---|---|---|",
]
lines += [f"| {k} | {b[k]} | {a[k]} |" for k in b]
text = "\n".join(lines)
print(text)
os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
with open(args.out, "w", encoding="utf-8") as f:
    f.write(text + "\n")
print(f"\nSaved: {args.out}")