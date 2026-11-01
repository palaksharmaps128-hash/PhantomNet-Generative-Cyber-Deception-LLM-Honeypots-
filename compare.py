"""Compare two evaluation runs (before / after) and print a markdown table.

Usage:
    python compare.py
    python compare.py evaluation/results_A.csv evaluation/results_B.csv
"""
import csv
import math
import os
import statistics
import sys

BEFORE = "evaluation/results_gemini-3.1-flash-lite.csv"
AFTER = "evaluation/results_gemini-3.1-flash-lite_static.csv"
before_path = sys.argv[1] if len(sys.argv) > 2 else BEFORE
after_path = sys.argv[2] if len(sys.argv) > 2 else AFTER


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


b, a = stats(load(before_path)), stats(load(after_path))
lines = [
    "# Before / after comparison",
    "",
    f"Before: `{before_path}`",
    f"After: `{after_path}`",
    "",
    "| Metric | Before | After |",
    "|---|---|---|",
]
lines += [f"| {k} | {b[k]} | {a[k]} |" for k in b]
text = "\n".join(lines)
print(text)
os.makedirs("evaluation", exist_ok=True)
with open("evaluation/comparison.md", "w", encoding="utf-8") as f:
    f.write(text + "\n")
print("\nSaved: evaluation/comparison.md")